from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from ... import texts as t
from ...keyboards import admin_menu_keyboard, cancel_keyboard
from ...settings_repo import get_pricing, set_setting
from ...states import AdminPricing
from .base import AdminOnlyMiddleware

router = Router(name="admin_pricing")
router.message.middleware(AdminOnlyMiddleware())


@router.message(F.text == t.ADMIN_MENU_PRICING)
async def show_pricing(message: Message, state: FSMContext):
    pricing = await get_pricing()
    await message.answer(
        t.PRICING_CURRENT.format(
            base_price=int(pricing["base_price"]),
            price_per_user=int(pricing["price_per_user"]),
            price_per_month=int(pricing["price_per_month"]),
            price_per_gb=int(pricing["price_per_gb"]),
        )
    )
    await state.set_state(AdminPricing.base_price)
    await message.answer(t.ASK_BASE_PRICE, reply_markup=cancel_keyboard())


def _parse_amount(text: str) -> int | None:
    try:
        value = int(text.strip())
        return value if value >= 0 else None
    except ValueError:
        return None


@router.message(AdminPricing.base_price)
async def set_base_price(message: Message, state: FSMContext):
    value = _parse_amount(message.text)
    if value is None:
        await message.answer(t.INVALID_NUMBER)
        return
    await state.update_data(base_price=value)
    await state.set_state(AdminPricing.price_per_user)
    await message.answer(t.ASK_PRICE_PER_USER)


@router.message(AdminPricing.price_per_user)
async def set_price_per_user(message: Message, state: FSMContext):
    value = _parse_amount(message.text)
    if value is None:
        await message.answer(t.INVALID_NUMBER)
        return
    await state.update_data(price_per_user=value)
    await state.set_state(AdminPricing.price_per_month)
    await message.answer(t.ASK_PRICE_PER_MONTH)


@router.message(AdminPricing.price_per_month)
async def set_price_per_month(message: Message, state: FSMContext):
    value = _parse_amount(message.text)
    if value is None:
        await message.answer(t.INVALID_NUMBER)
        return
    await state.update_data(price_per_month=value)
    await state.set_state(AdminPricing.price_per_gb)
    await message.answer(t.ASK_PRICE_PER_GB)


@router.message(AdminPricing.price_per_gb)
async def set_price_per_gb(message: Message, state: FSMContext):
    value = _parse_amount(message.text)
    if value is None:
        await message.answer(t.INVALID_NUMBER)
        return
    data = await state.get_data()
    await set_setting("base_price", str(data["base_price"]))
    await set_setting("price_per_user", str(data["price_per_user"]))
    await set_setting("price_per_month", str(data["price_per_month"]))
    await set_setting("price_per_gb", str(value))
    await state.clear()
    await message.answer(t.PRICING_UPDATED, reply_markup=admin_menu_keyboard())
