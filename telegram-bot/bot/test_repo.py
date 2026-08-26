"""Test service management."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from .db import async_session
from .models import TestServiceUsage, Service
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
        "provider": await get_setting("test_provider"),
        "wholesaler_limit": int(await get_setting("test_wholesaler_limit")),
    }


async def count_user_tests(telegram_id: int) -> int:
    """Count how many test services a user has been given (price=0 services)."""
    async with async_session() as session:
        result = await session.execute(
            select(Service).where(
                Service.owner_telegram_id == telegram_id,
                Service.price == 0,
            )
        )
        return len(result.scalars().all())


async def clear_wholesaler_test_services(telegram_id: int) -> int:
    """Delete price=0 services for a specific user to reset their test count."""
    async with async_session() as session:
        result = await session.execute(
            select(Service).where(
                Service.owner_telegram_id == telegram_id,
                Service.price == 0,
            )
        )
        services = result.scalars().all()
        count = len(services)
        for s in services:
            await session.delete(s)
        await session.commit()
        return count


async def clear_all_wholesaler_test_services() -> int:
    """Delete all price=0 services for all wholesalers."""
    from .models import Wholesaler

    async with async_session() as session:
        w_result = await session.execute(select(Wholesaler.telegram_id))
        wholesaler_ids = [row[0] for row in w_result.all()]
        if not wholesaler_ids:
            return 0
        result = await session.execute(
            select(Service).where(
                Service.owner_telegram_id.in_(wholesaler_ids),
                Service.price == 0,
            )
        )
        services = result.scalars().all()
        count = len(services)
        for s in services:
            await session.delete(s)
        await session.commit()
        return count
