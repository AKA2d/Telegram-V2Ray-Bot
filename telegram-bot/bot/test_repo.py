"""Test service management."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from .db import async_session
from .models import TestServiceUsage
from .settings_repo import get_setting


async def has_used_test(telegram_id: int) -> bool:
    async with async_session() as session:
        result = await session.execute(
            select(TestServiceUsage).where(TestServiceUsage.telegram_id == telegram_id)
        )
        return result.scalars().first() is not None


async def mark_test_used(telegram_id: int) -> None:
    async with async_session() as session:
        usage = TestServiceUsage(telegram_id=telegram_id)
        session.add(usage)
        await session.commit()


async def clear_all_test_users() -> int:
    async with async_session() as session:
        result = await session.execute(select(TestServiceUsage))
        users = result.scalars().all()
        count = len(users)
        for u in users:
            await session.delete(u)
        await session.commit()
        return count


async def get_test_settings() -> dict:
    return {
        "traffic_gb": float(await get_setting("test_traffic_gb")),
        "days": int(await get_setting("test_days")),
        "enabled": (await get_setting("test_enabled")) == "1",
    }
