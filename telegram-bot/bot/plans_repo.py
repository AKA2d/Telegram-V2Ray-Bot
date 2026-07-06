"""Helpers to manage admin-defined subscription plans."""

from decimal import Decimal

from sqlalchemy import select

from .db import async_session
from .models import Plan


async def list_active_plans() -> list[Plan]:
    async with async_session() as session:
        result = await session.execute(
            select(Plan).where(Plan.is_active == True).order_by(Plan.display_order)  # noqa: E712
        )
        return list(result.scalars().all())


async def list_all_plans() -> list[Plan]:
    async with async_session() as session:
        result = await session.execute(select(Plan).order_by(Plan.display_order))
        return list(result.scalars().all())


async def get_plan(plan_id: int) -> Plan | None:
    async with async_session() as session:
        return await session.get(Plan, plan_id)


async def create_plan(name: str, user_count: int, months: int, traffic_gb: int, price: Decimal) -> Plan:
    async with async_session() as session:
        result = await session.execute(select(Plan))
        count = len(result.scalars().all())
        plan = Plan(
            name=name,
            user_count=user_count,
            months=months,
            traffic_gb=traffic_gb,
            price=price,
            is_active=True,
            display_order=count,
        )
        session.add(plan)
        await session.commit()
        await session.refresh(plan)
        return plan


async def remove_plan(plan_id: int) -> None:
    async with async_session() as session:
        plan = await session.get(Plan, plan_id)
        if plan:
            await session.delete(plan)
            await session.commit()


async def toggle_plan_active(plan_id: int) -> None:
    async with async_session() as session:
        plan = await session.get(Plan, plan_id)
        if plan:
            plan.is_active = not plan.is_active
            await session.commit()
