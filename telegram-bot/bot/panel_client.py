"""Adapter around the PasarGuard panel REST API.

All panel-specific HTTP logic is isolated here so bot handlers never talk to
the panel directly. Endpoint paths are based on the PasarGuard OpenAPI docs
(https://docs.pasarguard.org/en) as of the time this was written; if the
deployed panel version differs, update the paths in one place: this file.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

import httpx

from .config import PANEL_BASE_URL, PANEL_PASSWORD, PANEL_USERNAME

logger = logging.getLogger("panel_client")


class PanelAPIError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


@dataclass
class PanelUser:
    username: str
    uuid: str | None
    subscription_link: str | None
    status: str
    raw: dict = field(default_factory=dict)


class PasarGuardClient:
    """Thin async adapter over the PasarGuard admin API."""

    def __init__(self, base_url: str = PANEL_BASE_URL, username: str = PANEL_USERNAME, password: str = PANEL_PASSWORD):
        self._base_url = base_url
        self._username = username
        self._password = password
        self._token: str | None = None
        self._token_expires_at: float = 0.0
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=20.0)

    async def close(self) -> None:
        await self._client.aclose()

    # ---- auth -----------------------------------------------------------

    async def _login(self) -> None:
        resp = await self._client.post(
            "/api/admin/token",
            data={"username": self._username, "password": self._password},
        )
        if resp.status_code != 200:
            raise PanelAPIError(f"Panel login failed: {resp.status_code} {resp.text}", resp.status_code)
        data = resp.json()
        self._token = data.get("access_token") or data.get("token")
        if not self._token:
            raise PanelAPIError("Panel login response missing access token")
        # PasarGuard tokens are typically long-lived; refresh proactively every hour.
        self._token_expires_at = time.time() + 3600

    async def _ensure_token(self) -> None:
        if not self._token or time.time() >= self._token_expires_at:
            await self._login()

    async def _request(self, method: str, path: str, retry: bool = True, **kwargs) -> httpx.Response:
        await self._ensure_token()
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self._token}"
        resp = await self._client.request(method, path, headers=headers, **kwargs)
        if resp.status_code == 401 and retry:
            logger.warning("Panel returned 401, re-authenticating and retrying %s %s", method, path)
            self._token = None
            await self._ensure_token()
            return await self._request(method, path, retry=False, **kwargs)
        return resp

    # ---- nodes / inbounds -------------------------------------------------

    async def list_inbounds(self) -> list[dict]:
        resp = await self._request("GET", "/api/inbounds")
        if resp.status_code != 200:
            raise PanelAPIError(f"Failed to list inbounds: {resp.status_code} {resp.text}", resp.status_code)
        data = resp.json()
        return data if isinstance(data, list) else data.get("inbounds", [])

    async def list_nodes(self) -> list[dict]:
        resp = await self._request("GET", "/api/nodes")
        if resp.status_code != 200:
            raise PanelAPIError(f"Failed to list nodes: {resp.status_code} {resp.text}", resp.status_code)
        data = resp.json()
        return data if isinstance(data, list) else data.get("nodes", [])

    # ---- user lifecycle ---------------------------------------------------

    async def create_user(
        self,
        username: str,
        data_limit_bytes: int,
        duration_seconds: int,
        proxies: dict | None = None,
        inbounds: dict | None = None,
    ) -> PanelUser:
        # The panel only accepts status "on_hold" or "active" at creation time
        # (it rejects "disabled" with a 422). on_hold also requires
        # on_hold_expire_duration (seconds) instead of an absolute expire
        # timestamp. Since new orders must stay inert until payment is
        # approved, we create as "on_hold" and then immediately flip it to
        # "disabled" with a follow-up PUT (this preserves on_hold_expire_duration
        # for later). Approval then calls enable_user() to set it "active" with
        # an explicit expire = now + duration.
        payload = {
            "username": username,
            "status": "on_hold",
            "data_limit": data_limit_bytes,
            "expire": 0,
            "on_hold_expire_duration": duration_seconds,
            "proxies": proxies or {"vless": {}, "vmess": {}},
        }
        if inbounds:
            payload["inbounds"] = inbounds
        resp = await self._request("POST", "/api/user", json=payload)
        if resp.status_code not in (200, 201):
            raise PanelAPIError(f"Failed to create panel user: {resp.status_code} {resp.text}", resp.status_code)
        data = resp.json()

        disable_resp = await self._request("PUT", f"/api/user/{username}", json={"status": "disabled"})
        if disable_resp.status_code == 200:
            data = disable_resp.json()
        else:
            logger.warning(
                "Created panel user %s but failed to disable it: %s %s",
                username,
                disable_resp.status_code,
                disable_resp.text,
            )

        return PanelUser(
            username=data.get("username", username),
            uuid=None,
            subscription_link=data.get("subscription_url") or data.get("links", [None])[0],
            status=data.get("status", "disabled"),
            raw=data,
        )

    async def get_user(self, username_or_uuid: str) -> PanelUser:
        resp = await self._request("GET", f"/api/user/{username_or_uuid}")
        if resp.status_code != 200:
            raise PanelAPIError(f"Failed to fetch panel user: {resp.status_code} {resp.text}", resp.status_code)
        data = resp.json()
        return PanelUser(
            username=data.get("username", username_or_uuid),
            uuid=None,
            subscription_link=data.get("subscription_url"),
            status=data.get("status", "unknown"),
            raw=data,
        )

    async def enable_user(self, username_or_uuid: str, duration_seconds: int | None = None) -> None:
        # Activating a user coming out of "on_hold" does NOT automatically
        # convert on_hold_expire_duration into a real expire timestamp - the
        # panel leaves expire=null (unlimited) unless we set it explicitly.
        # When duration_seconds is known (new service approval), compute and
        # send an explicit expire = now + duration alongside status=active.
        payload = {"status": "active"}
        if duration_seconds is not None:
            payload["expire"] = int(time.time()) + duration_seconds
        await self._modify_status(username_or_uuid, payload)

    async def disable_user(self, username_or_uuid: str) -> None:
        await self._modify_status(username_or_uuid, {"status": "disabled"})

    async def _modify_status(self, username_or_uuid: str, payload: dict) -> None:
        resp = await self._request("PUT", f"/api/user/{username_or_uuid}", json=payload)
        if resp.status_code != 200:
            raise PanelAPIError(
                f"Failed to update status for {username_or_uuid}: {resp.status_code} {resp.text}",
                resp.status_code,
            )

    async def regenerate_subscription(self, username_or_uuid: str) -> PanelUser:
        resp = await self._request("POST", f"/api/user/{username_or_uuid}/reset")
        if resp.status_code != 200:
            raise PanelAPIError(
                f"Failed to regenerate subscription for {username_or_uuid}: {resp.status_code} {resp.text}",
                resp.status_code,
            )
        data = resp.json()
        return PanelUser(
            username=data.get("username", username_or_uuid),
            uuid=None,
            subscription_link=data.get("subscription_url"),
            status=data.get("status", "active"),
            raw=data,
        )

    async def delete_user(self, username_or_uuid: str) -> None:
        resp = await self._request("DELETE", f"/api/user/{username_or_uuid}")
        if resp.status_code not in (200, 204):
            raise PanelAPIError(
                f"Failed to delete user {username_or_uuid}: {resp.status_code} {resp.text}", resp.status_code
            )

    # ---- tunnel management --------------------------------------------------

    async def add_tunnel_to_user(self, username_or_uuid: str, tunnel_inbound_tag: str) -> None:
        user = await self.get_user(username_or_uuid)
        inbounds = dict(user.raw.get("inbounds", {}))
        for protocol, tags in inbounds.items():
            if tunnel_inbound_tag not in tags:
                tags.append(tunnel_inbound_tag)
        resp = await self._request("PUT", f"/api/user/{username_or_uuid}", json={"inbounds": inbounds})
        if resp.status_code != 200:
            raise PanelAPIError(f"Failed to add tunnel: {resp.status_code} {resp.text}", resp.status_code)

    async def remove_tunnel_from_user(self, username_or_uuid: str, tunnel_inbound_tag: str) -> None:
        user = await self.get_user(username_or_uuid)
        inbounds = dict(user.raw.get("inbounds", {}))
        for protocol, tags in inbounds.items():
            if tunnel_inbound_tag in tags:
                tags.remove(tunnel_inbound_tag)
        resp = await self._request("PUT", f"/api/user/{username_or_uuid}", json={"inbounds": inbounds})
        if resp.status_code != 200:
            raise PanelAPIError(f"Failed to remove tunnel: {resp.status_code} {resp.text}", resp.status_code)


panel_client = PasarGuardClient()
