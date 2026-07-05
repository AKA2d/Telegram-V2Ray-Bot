"""Helpers to read/write admin_settings key-value pairs."""

from decimal import Decimal

from sqlalchemy import select

from .db import async_session
from .models import AdminSetting

DEFAULTS = {
    "base_price": "50000",
    "price_per_user": "20000",
    "price_per_month": "80000",
    "price_per_gb": "5000",
}


async def get_setting(key: str) -> str:
    async with async_session() as session:
        row = await session.get(AdminSetting, key)
        if row:
            return row.value
        return DEFAULTS.get(key, "0")


async def set_setting(key: str, value: str) -> None:
    async with async_session() as session:
        row = await session.get(AdminSetting, key)
        if row:
            row.value = value
        else:
            session.add(AdminSetting(key=key, value=value))
        await session.commit()


async def get_pricing() -> dict[str, Decimal]:
    keys = ["base_price", "price_per_user", "price_per_month", "price_per_gb"]
    result = {}
    for key in keys:
        result[key] = Decimal(await get_setting(key))
    return result


async def calculate_price(user_count: int, months: int, traffic_gb: int) -> Decimal:
    pricing = await get_pricing()
    extra_users = max(0, user_count - 1)
    price = (
        pricing["base_price"]
        + extra_users * pricing["price_per_user"]
        + months * pricing["price_per_month"]
        + traffic_gb * pricing["price_per_gb"]
    )
    return price
