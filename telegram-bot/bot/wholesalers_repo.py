from decimal import Decimal

from sqlalchemy import delete, select, func

from .db import async_session
from .models import Order, Service, User, Wholesaler


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


async def get_wholesaler_stats(telegram_id: int) -> dict:
    """Get stats for a single wholesaler."""
    async with async_session() as session:
        # Total services
        result = await session.execute(
            select(func.count(Service.id)).where(Service.owner_telegram_id == telegram_id)
        )
        total_services = result.scalar() or 0

        # Active services
        result = await session.execute(
            select(func.count(Service.id)).where(
                Service.owner_telegram_id == telegram_id,
                Service.status == "active"
            )
        )
        active_services = result.scalar() or 0

        # Total revenue from this wholesaler's orders
        result = await session.execute(
            select(func.coalesce(func.sum(Order.amount), 0)).where(
                Order.telegram_id == telegram_id,
                Order.status == "approved"
            )
        )
        total_revenue = int(result.scalar() or 0)

        # Total traffic sold
        result = await session.execute(
            select(func.coalesce(func.sum(Service.traffic_gb), 0)).where(
                Service.owner_telegram_id == telegram_id,
                Service.status == "active"
            )
        )
        total_traffic = int(float(result.scalar() or 0))

        # Wallet balance
        user = await session.get(User, telegram_id)
        wallet_balance = int(user.wallet_balance) if user else 0

    return {
        "total_services": total_services,
        "active_services": active_services,
        "total_revenue": total_revenue,
        "total_traffic": total_traffic,
        "wallet_balance": wallet_balance,
    }


async def get_all_wholesalers_stats() -> dict:
    """Get aggregate stats for all wholesalers."""
    async with async_session() as session:
        # Get all wholesaler IDs
        result = await session.execute(select(Wholesaler.telegram_id))
        wholesaler_ids = [row[0] for row in result.all()]

        if not wholesaler_ids:
            return {
                "count": 0,
                "total_services": 0,
                "active_services": 0,
                "total_revenue": 0,
                "total_traffic": 0,
                "total_wallet": 0,
            }

        # Total services
        result = await session.execute(
            select(func.count(Service.id)).where(Service.owner_telegram_id.in_(wholesaler_ids))
        )
        total_services = result.scalar() or 0

        # Active services
        result = await session.execute(
            select(func.count(Service.id)).where(
                Service.owner_telegram_id.in_(wholesaler_ids),
                Service.status == "active"
            )
        )
        active_services = result.scalar() or 0

        # Total revenue
        result = await session.execute(
            select(func.coalesce(func.sum(Order.amount), 0)).where(
                Order.telegram_id.in_(wholesaler_ids),
                Order.status == "approved"
            )
        )
        total_revenue = int(result.scalar() or 0)

        # Total traffic
        result = await session.execute(
            select(func.coalesce(func.sum(Service.traffic_gb), 0)).where(
                Service.owner_telegram_id.in_(wholesaler_ids),
                Service.status == "active"
            )
        )
        total_traffic = int(float(result.scalar() or 0))

        # Total wallet balance
        result = await session.execute(
            select(func.coalesce(func.sum(User.wallet_balance), 0)).where(
                User.telegram_id.in_(wholesaler_ids)
            )
        )
        total_wallet = int(result.scalar() or 0)

    return {
        "count": len(wholesaler_ids),
        "total_services": total_services,
        "active_services": active_services,
        "total_revenue": total_revenue,
        "total_traffic": total_traffic,
        "total_wallet": total_wallet,
    }
