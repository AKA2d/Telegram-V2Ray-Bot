from sqlalchemy import select, update

from .db import async_session
from .models import Order


async def create_order(**kwargs) -> Order:
    async with async_session() as session:
        order = Order(**kwargs)
        session.add(order)
        await session.commit()
        await session.refresh(order)
        return order


async def get_order(order_id: int) -> Order | None:
    async with async_session() as session:
        return await session.get(Order, order_id)


async def update_order(order_id: int, **kwargs) -> Order | None:
    async with async_session() as session:
        order = await session.get(Order, order_id)
        if not order:
            return None
        for key, value in kwargs.items():
            setattr(order, key, value)
        await session.commit()
        await session.refresh(order)
        return order


async def transition_order_status(order_id: int, expected_status: str, new_status: str) -> bool:
    """Atomically claim an order transition so duplicate callbacks are safe."""
    async with async_session() as session:
        result = await session.execute(
            update(Order)
            .where(Order.id == order_id, Order.status == expected_status)
            .values(status=new_status)
        )
        await session.commit()
        return result.rowcount == 1


async def list_pending_orders() -> list[Order]:
    async with async_session() as session:
        result = await session.execute(
            select(Order).where(Order.status == "awaiting_admin_review").order_by(Order.submitted_at)
        )
        return list(result.scalars().all())


async def count_user_orders(telegram_id: int) -> int:
    async with async_session() as session:
        result = await session.execute(select(Order).where(Order.telegram_id == telegram_id))
        return len(list(result.scalars().all()))
