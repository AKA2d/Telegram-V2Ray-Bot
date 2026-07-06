from dotenv import load_dotenv
import os
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

load_dotenv()

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ADMIN_TELEGRAM_ID = int(os.environ["ADMIN_TELEGRAM_ID"])


def _normalize_panel_base_url(raw: str) -> str:
    url = raw.strip()
    # Strip a trailing hash-router fragment (e.g. copied from a browser address
    # bar like https://host/dashboard/#/login) which httpx would otherwise
    # silently re-append to the end of every request URL.
    url = url.split("#", 1)[0]
    url = url.rstrip("/")
    # The panel's web UI is commonly served under /dashboard, but the REST API
    # itself lives at the domain root. Strip a trailing /dashboard segment.
    if url.endswith("/dashboard"):
        url = url[: -len("/dashboard")]
    return url.rstrip("/")


PANEL_BASE_URL = _normalize_panel_base_url(os.environ["PANEL_BASE_URL"])
PANEL_USERNAME = os.environ["PANEL_USERNAME"]
PANEL_PASSWORD = os.environ["PANEL_PASSWORD"]

DATABASE_URL = os.environ["DATABASE_URL"]


def _to_async_url(url: str) -> str:
    # SQLAlchemy async needs the asyncpg driver in the URL.
    url = url.replace("postgresql://", "postgresql+asyncpg://", 1).replace(
        "postgres://", "postgresql+asyncpg://", 1
    )
    # asyncpg does not understand libpq-style query params like sslmode; drop them.
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query))
    query.pop("sslmode", None)
    query.pop("channel_binding", None)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


ASYNC_DATABASE_URL = _to_async_url(DATABASE_URL)

# Optional: Telegram channel that customers must join before using the bot.
# Set REQUIRED_CHANNEL_ID (e.g. @mychannel or -100123456789) to enable the gate.
REQUIRED_CHANNEL_ID = os.environ.get("REQUIRED_CHANNEL_ID", "").strip() or None

# Comma-separated list of "direct" node/inbound tags in the panel. Any node NOT
# in this list is treated as a tunnel node and excluded from default account creation.
DIRECT_NODE_TAGS = [
    tag.strip() for tag in os.environ.get("DIRECT_NODE_TAGS", "").split(",") if tag.strip()
]
