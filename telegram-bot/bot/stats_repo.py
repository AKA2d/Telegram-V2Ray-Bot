"""Calculate time-based sales stats from the database."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func

from .db import async_session
from .models import Order, Service


async def _sum_orders_and_traffic(start_date: datetime) -> tuple[int, int]:
    """Sum order amounts and service traffic for orders approved after start_date."""
    async with async_session() as session:
        result = await session.execute(
            select(
                func.coalesce(func.sum(Order.amount), 0),
            ).where(
                Order.status == "approved",
                Order.type == "new_service",
                Order.reviewed_at >= start_date,
            )
        )
        amount = result.scalar() or 0

        # Get traffic from services created in this period
        result = await session.execute(
            select(
                func.coalesce(func.sum(Service.traffic_gb), 0),
            ).where(
                Service.status == "active",
                Service.price > 0,
                Service.created_at >= start_date,
            )
        )
        traffic = result.scalar() or 0

    return int(amount), int(traffic)


async def get_period_stats() -> dict:
    """Get daily, weekly, monthly, and total stats."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())
    month_start = today_start.replace(day=1)

    daily_amount, daily_traffic = await _sum_orders_and_traffic(today_start)
    weekly_amount, weekly_traffic = await _sum_orders_and_traffic(week_start)
    monthly_amount, monthly_traffic = await _sum_orders_and_traffic(month_start)

    return {
        "daily_amount": f"{daily_amount:,}",
        "daily_traffic": daily_traffic,
        "weekly_amount": f"{weekly_amount:,}",
        "weekly_traffic": weekly_traffic,
        "monthly_amount": f"{monthly_amount:,}",
        "monthly_traffic": monthly_traffic,
    }
