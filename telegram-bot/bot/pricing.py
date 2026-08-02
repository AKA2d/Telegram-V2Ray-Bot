"""Centralized price and discount calculations for customer-facing flows."""

from decimal import Decimal, ROUND_HALF_UP
from html import escape

from .settings_repo import get_setting


def discounted_price(original: int | Decimal, discount_percent: int) -> int:
    """Return a whole-toman price after applying a validated percentage."""
    amount = Decimal(original)
    return int((amount * (100 - discount_percent) / 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def format_price(original: int | Decimal, discounted: int | Decimal) -> str:
    """Format a price for Telegram HTML, striking out only when discounted."""
    original_int = int(original)
    discounted_int = int(discounted)
    if original_int == discounted_int:
        return f"{discounted_int:,}"
    return f"<b>{discounted_int:,}</b> → <s>{original_int:,}</s>"


def base_plan_price(plan, is_wholesaler: bool) -> Decimal:
    return plan.wholesale_price if is_wholesaler and plan.wholesale_price is not None else plan.price


async def get_discount_percent(is_wholesaler: bool) -> int:
    key = "wholesaler_discount_percent" if is_wholesaler else "user_discount_percent"
    try:
        value = int(await get_setting(key))
    except ValueError:
        return 0
    return max(0, min(value, 99))


async def plan_price_quote(plan, is_wholesaler: bool) -> tuple[Decimal, int, int]:
    """Return original base price, discounted price, and the rate used."""
    original = base_plan_price(plan, is_wholesaler)
    percent = await get_discount_percent(is_wholesaler)
    return original, discounted_price(original, percent), percent


def safe_plan_name(name: str) -> str:
    return escape(name)
