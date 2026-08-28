#!/usr/bin/env python3
"""Migration: fix unlimited services whose Xenet duration is shorter than the DB record.

The Xenet API only supports creating/renewing accounts for 1 month at a time.
Before the multi-month fix, a plan with N months only created 1 month on Xenet.
This script detects affected services and renews them for the missing months.

Usage:
    python -m scripts.fix_xenet_multi_month          # dry-run (default)
    python -m scripts.fix_xenet_multi_month --apply   # actually renew
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import math
import sys
from datetime import datetime, timezone

# Allow running from the telegram-bot directory
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

from bot.db import async_session  # noqa: E402
from bot.models import Service  # noqa: E402
from bot.xenet_client import XenetAPIError, xenet_client  # noqa: E402

from sqlalchemy import select

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


async def find_affected_services() -> list[Service]:
    """Return active unlimited services with months > 1 and a xenet_account_id."""
    async with async_session() as session:
        result = await session.execute(
            select(Service).where(
                Service.service_type == "unlimited",
                Service.status == "active",
                Service.months > 1,
                Service.xenet_account_id.isnot(None),
            )
        )
        return list(result.scalars().all())


def _days_remaining(expires_at: datetime | None) -> float:
    """How many days remain until *expires_at* (can be negative if expired)."""
    if expires_at is None:
        return 0.0
    now = datetime.now(timezone.utc)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return (expires_at - now).total_seconds() / 86400


async def fix_service(service: Service, apply: bool) -> str:
    """Check *service* against Xenet and renew if needed.

    Returns a human-readable status line.
    """
    xenet_id = service.xenet_account_id
    if xenet_id is None:
        return f"#{service.id}: skipped (no xenet_account_id)"

    # --- Query current Xenet state ------------------------------------------
    try:
        xenet_info = await xenet_client.get_v2_account(xenet_id)
    except XenetAPIError as exc:
        return f"#{service.id}: Xenet API error querying account {xenet_id}: {exc}"

    xenet_days_left = xenet_info.get("days_left", 0)

    # --- Determine how many extra months the DB expects ----------------------
    db_days_remaining = _days_remaining(service.expires_at)
    if db_days_remaining <= 0:
        return (
            f"#{service.id}: DB service expired "
            f"(expires_at={service.expires_at}), skipping"
        )

    # The Xenet account should ideally have at least as many days as the DB.
    # We also add a small buffer (2 days) to account for rounding.
    days_deficit = db_days_remaining - xenet_days_left + 2
    if days_deficit <= 0:
        return (
            f"#{service.id}: OK — Xenet {xenet_days_left}d >= "
            f"DB {db_days_remaining:.0f}d (no renewal needed)"
        )

    # Convert deficit to whole months (round up, minimum 1)
    months_to_add = max(1, math.ceil(days_deficit / 30))

    status = (
        f"#{service.id}: DEFICIT — Xenet {xenet_days_left}d vs "
        f"DB {db_days_remaining:.0f}d → renewing {months_to_add} month(s)"
    )

    if apply:
        try:
            await xenet_client.renew_v2_account_multi(
                xenet_id,
                months_to_add,
                idempotency_prefix=f"migration_fix_{service.id}",
            )
            status += " ✅ done"
        except XenetAPIError as exc:
            status += f" ❌ failed: {exc}"

    return status


async def main(apply: bool = False) -> None:
    affected = await find_affected_services()
    if not affected:
        logger.info("No affected unlimited services found. Nothing to fix.")
        return

    logger.info(
        "Found %d unlimited service(s) with months > 1 and xenet_account_id.",
        len(affected),
    )
    logger.info("Mode: %s", "APPLY (renewing on Xenet)" if apply else "DRY-RUN (no changes)")
    print()

    for svc in affected:
        result = await fix_service(svc, apply=apply)
        print(result)

    print()
    if not apply:
        logger.info(
            "Dry-run complete. Re-run with --apply to execute renewals."
        )
    else:
        logger.info("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fix unlimited services whose Xenet duration is shorter than the DB record."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually renew on Xenet (default is dry-run).",
    )
    args = parser.parse_args()
    asyncio.run(main(apply=args.apply))
