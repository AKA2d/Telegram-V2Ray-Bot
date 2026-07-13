"""Helpers to read/write admin_settings key-value pairs."""

from sqlalchemy import select

from .db import async_session
from .models import AdminSetting

DEFAULTS: dict[str, str] = {
    "sales_closed": "0",
    "sold_amount": "0",
    "sold_traffic": "0",
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
