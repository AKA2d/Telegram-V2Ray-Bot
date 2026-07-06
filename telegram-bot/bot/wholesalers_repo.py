from decimal import Decimal

from sqlalchemy import delete, select

from .db import async_session
from .models import User, Wholesaler


async def list_wholesalers() -> list[Wholesaler]:
    async with async_session() as session:
        result = await session.execute(select(Wholesaler).order_by(Wholesaler.created_at))
        return result.scalars().all()


async def get_wholesaler_by_telegram_id(telegram_id: int) -> Wholesaler | None:
    async with async_session() as session:
        return await session.get(Wholesaler, telegram_id)


async def is_wholesaler(telegram_id: int) -> bool:
    async with async_session() as session:
        wholesaler = await session.get(Wholesaler, telegram_id)
        return wholesaler is not None


async def create_wholesaler(telegram_id: int, username: str | None = None, first_name: str | None = None) -> Wholesaler:
    async with async_session() as session:
        user = await session.get(User, telegram_id)
        if not user:
            user = User(telegram_id=telegram_id, username=username, first_name=first_name)
            session.add(user)
            await session.commit()
            await session.refresh(user)

        wholesaler = await session.get(Wholesaler, telegram_id)
        if wholesaler:
            return wholesaler

        wholesaler = Wholesaler(telegram_id=telegram_id)
        session.add(wholesaler)
        await session.commit()
        await session.refresh(wholesaler)
        return wholesaler


async def remove_wholesaler(telegram_id: int) -> None:
    async with async_session() as session:
        wholesaler = await session.get(Wholesaler, telegram_id)
        if wholesaler:
            await session.delete(wholesaler)
            await session.commit()
