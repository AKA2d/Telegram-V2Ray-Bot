---
name: PasarGuard/Marzban-style panel user status quirks
description: Non-obvious rules for creating and activating panel users via the PasarGuard REST API (status enum, on_hold, expire).
---

Observed against a live PasarGuard panel (Marzban-family V2Ray panel), via `/api/user` and `/api/user/{username}`:

- `POST /api/user` (create) only accepts `status` of `on_hold` or `active` — `disabled` is rejected with a 422 (`status must be in {on_hold, active}`).
- `status: "on_hold"` at creation requires `on_hold_expire_duration` (seconds) instead of an absolute `expire` timestamp; passing `expire` normally without this errors ("User cannot be on hold without a valid on_hold_expire_duration").
- To create a user that should start **disabled** (e.g. inert until payment is approved): create as `on_hold` with `on_hold_expire_duration` set, then immediately issue a follow-up `PUT /api/user/{username}` with `{"status": "disabled"}`. This preserves `on_hold_expire_duration` for later.
- **Activating** a user (`PUT .../{username}` with `{"status": "active"}`) does NOT auto-convert `on_hold_expire_duration` into a real `expire` timestamp — the panel silently leaves `expire: null` (i.e. unlimited/no expiry) unless you explicitly pass `expire` in that same PUT call. Always send `{"status": "active", "expire": <now + duration>}` together on activation.
- The panel does not return a stable per-user `uuid` field in create/get/modify responses — treat `username` as the durable identifier for all lifecycle calls (enable/disable/regenerate/tunnel-add). Don't fabricate a random uuid as a fallback; store `None` and fall back to username everywhere.

**Why:** These are silent/non-obvious validation and behavior quirks (422 on plausible payloads, and a silently-wrong "unlimited" expiry) discovered only by direct API probing — none of it is documented behavior you'd guess from the panel's admin UI.

**How to apply:** Any future work on `telegram-bot/bot/panel_client.py` involving user creation, status transitions, or identifiers should follow this create→disable→activate pattern and always pass explicit `expire` on activation.
