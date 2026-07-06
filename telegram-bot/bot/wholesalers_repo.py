from decimal import Decimal

from sqlalchemy import delete, select

from .db import async_session
from .models import User, Wholesaler, WholesalerPlan, WholesalePlan


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
        await session.execute(delete(WholesalerPlan).where(WholesalerPlan.wholesaler_id == telegram_id))
        wholesaler = await session.get(Wholesaler, telegram_id)
        if wholesaler:
            await session.delete(wholesaler)
            await session.commit()


async def list_wholesale_plans() -> list[WholesalePlan]:
    async with async_session() as session:
        result = await session.execute(select(WholesalePlan).order_by(WholesalePlan.display_order))
        return result.scalars().all()


async def list_active_wholesale_plans() -> list[WholesalePlan]:
    async with async_session() as session:
        result = await session.execute(
            select(WholesalePlan).where(WholesalePlan.is_active == True).order_by(WholesalePlan.display_order)  # noqa: E712
        )
        return result.scalars().all()


async def list_active_wholesale_plans_for_user(telegram_id: int) -> list[WholesalePlan]:
    async with async_session() as session:
        result = await session.execute(
            select(WholesalePlan)
            .join(WholesalerPlan)
            .where(WholesalerPlan.wholesaler_id == telegram_id, WholesalePlan.is_active == True)
            .order_by(WholesalePlan.display_order)
        )
        return result.scalars().all()


async def list_assigned_wholesale_plans(telegram_id: int) -> list[WholesalePlan]:
    async with async_session() as session:
        result = await session.execute(
            select(WholesalePlan)
            .join(WholesalerPlan)
            .where(WholesalerPlan.wholesaler_id == telegram_id)
            .order_by(WholesalePlan.display_order)
        )
        return result.scalars().all()


async def get_wholesale_plan(plan_id: int) -> WholesalePlan | None:
    async with async_session() as session:
        return await session.get(WholesalePlan, plan_id)


async def create_wholesale_plan(
    name: str,
    user_count: int,
    months: int,
    traffic_gb: int,
    price: Decimal,
) -> WholesalePlan:
    async with async_session() as session:
        plan = WholesalePlan(
            name=name,
            user_count=user_count,
            months=months,
            traffic_gb=traffic_gb,
            price=price,
        )
        session.add(plan)
        await session.commit()
        await session.refresh(plan)
        return plan


async def remove_wholesale_plan(plan_id: int) -> None:
    async with async_session() as session:
        await session.execute(delete(WholesalerPlan).where(WholesalerPlan.plan_id == plan_id))
        plan = await session.get(WholesalePlan, plan_id)
        if plan:
            await session.delete(plan)
            await session.commit()


async def toggle_wholesale_plan_active(plan_id: int) -> None:
    async with async_session() as session:
        plan = await session.get(WholesalePlan, plan_id)
        if plan:
            plan.is_active = not plan.is_active
            await session.commit()


async def assign_wholesale_plan(telegram_id: int, plan_id: int) -> None:
    async with async_session() as session:
        wholesaler = await session.get(Wholesaler, telegram_id)
        plan = await session.get(WholesalePlan, plan_id)
        if not wholesaler or not plan or not plan.is_active:
            return
        existing = await session.get(WholesalerPlan, (telegram_id, plan_id))
        if not existing:
            session.add(WholesalerPlan(wholesaler_id=telegram_id, plan_id=plan_id))
            await session.commit()


async def unassign_wholesale_plan(telegram_id: int, plan_id: int) -> None:
    async with async_session() as session:
        await session.execute(
            delete(WholesalerPlan).where(WholesalerPlan.wholesaler_id == telegram_id, WholesalerPlan.plan_id == plan_id)
        )
        await session.commit()
