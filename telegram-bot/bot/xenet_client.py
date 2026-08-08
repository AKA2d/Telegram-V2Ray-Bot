"""Adapter around the Xenet.space reseller API for unlimited V2Ray services."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import httpx

from .config import XENET_API_KEY, XENET_BASE_URL

logger = logging.getLogger("xenet_client")


class XenetAPIError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


@dataclass
class XenetV2Config:
    """Represents a V2Ray configuration from Xenet API."""
    id: int
    kind: str
    name: str
    sub_link: str
    users: int
    price_paid: int
    expire_date: str
    status: str
    days_left: int
    enabled: bool
    raw: dict | None = None


class XenetClient:
    """Thin async adapter ov    er the Xenet reseller API."""

    def __init__(self, api_key: str = XENET_API_KEY, base_url: str = XENET_BASE_URL):
        self._api_key = api_key
        self._base_url = base_url
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=20.0,
            headers={"Authorization": f"Bearer {self._api_key}"},
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        if not self._api_key:
            raise XenetAPIError("XENET_API_KEY is not configured")
        resp = await self._client.request(method, path, **kwargs)
        if resp.status_code == 401:
            raise XenetAPIError("Xenet API authentication failed", 401)
        if resp.status_code == 402:
            raise XenetAPIError("Insufficient balance on Xenet account", 402)
        if resp.status_code != 200:
            raise XenetAPIError(f"Xenet API error: {resp.status_code} {resp.text}", resp.status_code)
        return resp

    async def get_balance(self) -> dict:
        """Get current reseller balance and profile."""
        resp = await self._request("GET", "/me")
        data = resp.json()
        if not data.get("ok"):
            raise XenetAPIError(data.get("message", "Failed to get balance"))
        return data.get("reseller", {})

    async def get_prices(self) -> dict:
        """Get current pricing from Xenet."""
        resp = await self._request("GET", "/prices")
        data = resp.json()
        if not data.get("ok"):
            raise XenetAPIError(data.get("message", "Failed to get prices"))
        return data.get("prices", {})

    async def create_v2_account(self, users: int = 1, idempotency_key: str | None = None) -> XenetV2Config:
        """Create a new V2Ray account (1 month, unlimited traffic)."""
        payload = {"users": users}
        headers = {}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        resp = await self._request("POST", "/v2", json=payload, headers=headers)
        data = resp.json()
        if not data.get("ok"):
            raise XenetAPIError(data.get("message", "Failed to create V2 account"))

        config_data = data.get("config", {})
        return XenetV2Config(
            id=config_data.get("id", 0),
            kind=config_data.get("kind", "direct"),
            name=config_data.get("name", ""),
            sub_link=config_data.get("sub_link", ""),
            users=config_data.get("users", 1),
            price_paid=config_data.get("price_paid", 0),
            expire_date=config_data.get("expire_date", ""),
            status=config_data.get("status", "active"),
            days_left=config_data.get("days_left", 30),
            enabled=config_data.get("enabled", True),
            raw=config_data,
        )

    async def get_v2_account(self, account_id: int) -> dict:
        """Get V2Ray account status."""
        resp = await self._request("GET", f"/v2/{account_id}")
        data = resp.json()
        if not data.get("ok"):
            raise XenetAPIError(data.get("message", "Failed to get V2 account"))
        return data.get("config", data)

    async def get_v2_config(self, account_id: int) -> dict:
        """Get V2Ray subscription link."""
        resp = await self._request("GET", f"/v2/{account_id}/config")
        data = resp.json()
        if not data.get("ok"):
            raise XenetAPIError(data.get("message", "Failed to get V2 config"))
        return data

    async def renew_v2_account(self, account_id: int, idempotency_key: str | None = None) -> dict:
        """Renew V2Ray account for 1 month."""
        headers = {}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        resp = await self._request("POST", f"/v2/{account_id}/renew", headers=headers)
        data = resp.json()
        if not data.get("ok"):
            raise XenetAPIError(data.get("message", "Failed to renew V2 account"))
        return data

    async def toggle_v2_account(self, account_id: int) -> dict:
        """Toggle V2Ray account enabled/disabled."""
        resp = await self._request("POST", f"/v2/{account_id}/toggle")
        data = resp.json()
        if not data.get("ok"):
            raise XenetAPIError(data.get("message", "Failed to toggle V2 account"))
        return data

    async def refund_v2_account(self, account_id: int) -> dict:
        """Refund V2Ray account."""
        resp = await self._request("POST", f"/v2/{account_id}/refund")
        data = resp.json()
        if not data.get("ok"):
            raise XenetAPIError(data.get("message", "Failed to refund V2 account"))
        return data

    async def list_v2_accounts(self, page: int = 1, per_page: int = 25, kind: str | None = None) -> list[dict]:
        """List V2Ray accounts."""
        params = {"page": page, "per_page": per_page}
        if kind:
            params["kind"] = kind

        resp = await self._request("GET", "/v2", params=params)
        data = resp.json()
        if not data.get("ok"):
            raise XenetAPIError(data.get("message", "Failed to list V2 accounts"))
        return data.get("configs", [])


xenet_client = XenetClient()
