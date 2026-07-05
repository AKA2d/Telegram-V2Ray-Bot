# V2Ray Subscription Sales Telegram Bot

Persian-language Telegram bot for a single admin to sell V2Ray subscriptions via the PasarGuard panel REST API. Customers buy services, top up a wallet, and manage subscriptions; the admin reviews receipt-based payments, manages pricing/cards/tunnels, and messages customers — all through Telegram.

## Run & Operate

- Workflow **"Telegram Bot"** runs `cd telegram-bot && python main.py` (console output, long-running polling process — not a web artifact).
- Required env (all set as Replit Secrets): `TELEGRAM_BOT_TOKEN`, `ADMIN_TELEGRAM_ID`, `PANEL_BASE_URL`, `PANEL_USERNAME`, `PANEL_PASSWORD`, `DATABASE_URL` (Replit Postgres, auto-provisioned).
- Optional env: `REQUIRED_CHANNEL_ID` (forces channel-join gate before bot use), `DIRECT_NODE_TAGS` (comma-separated panel inbound tags treated as "direct"; anything else is treated as a tunnel node).
- DB tables are created automatically on startup via `init_db()` (SQLAlchemy `create_all`) — no separate migration step needed for this project.

## Stack

- Python 3.11, aiogram 3 (polling, `MemoryStorage` for FSM), SQLAlchemy async + asyncpg, httpx for panel calls.
- Lives at `telegram-bot/` in the repo root — **not** a pnpm-workspace artifact, it's a standalone Python service with its own workflow.

## Where things live

- `telegram-bot/main.py` — entrypoint; wires all routers, calls `init_db()`, starts polling.
- `telegram-bot/bot/config.py` — env vars, async DB URL normalization.
- `telegram-bot/bot/models.py` — User, Service, Order, Card, AdminSetting, WalletAuditLog.
- `telegram-bot/bot/panel_client.py` — PasarGuard panel HTTP client (login/token refresh, user CRUD, tunnel add/remove). Endpoint paths are best-effort per spec and may need adjustment against the real panel.
- `telegram-bot/bot/texts.py` — all Persian user-facing strings (single source of truth for copy).
- `telegram-bot/bot/handlers/` — customer flows (start, buy_service, wallet, manage_service, account_info, connect_guide).
- `telegram-bot/bot/handlers/admin/` — admin-only flows (orders review, pricing, customer lookup, wallet override, broadcast, direct message, cards, tunnel), gated by `AdminOnlyMiddleware` in `base.py`.

## Architecture decisions

- Postgres (not MySQL as originally spec'd) — user approved substitution since Replit provisions Postgres natively.
- Single admin identified by `ADMIN_TELEGRAM_ID`; all admin routers apply an `AdminOnlyMiddleware` rather than per-handler checks.
- Phase 2 features (increase users, renewal) are intentionally stubbed with a "coming soon" alert (`PHASE2_NOT_AVAILABLE`) per spec scope.
- Orders are idempotency-checked by status (`awaiting_admin_review` only) before admin approve/reject to prevent double-processing from duplicate button taps.

## Product

- Customer: buy a V2Ray service (choose user count/months/traffic → price → pay via card receipt → admin approval → service activated), top up wallet, view account info, look up/regenerate/manage owned services, view connection guides per platform/app.
- Admin: review pending orders (approve/reject with panel enable/disable), manage pricing formula, look up any customer, override wallet balances (audited), broadcast or direct-message users, rotate payment cards, add/remove VPN tunnels per account or globally.

## User preferences

- None recorded beyond the approved Postgres substitution.

## Gotchas

- Replit's Postgres connection string includes `sslmode`/`channel_binding` query params that `asyncpg` does not understand — `config.py` strips them before building the async SQLAlchemy URL. Any new DB URL handling must preserve this.
- This service does not use `PORT`/`BASE_PATH` like other artifacts — it's a background polling process, registered as a plain workflow, not through the artifacts system.

## Pointers

- See the `pnpm-workspace` skill for the rest of the monorepo (unrelated Node/TS artifacts) — the bot does not participate in that workspace.
