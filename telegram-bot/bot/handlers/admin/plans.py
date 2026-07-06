from decimal import Decimal

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from ... import texts as t
from ...keyboards import admin_plans_keyboard
from ...plans_repo import create_plan, get_plan, list_all_plans, remove_plan, toggle_plan_active
from ...states import AdminPlans
from .base import AdminOnlyMiddleware

router = Router(name="admin_plans")
router.message.middleware(AdminOnlyMiddleware())
router.callback_query.middleware(AdminOnlyMiddleware())


async def _show_plans(message: Message):
    plans = await list_all_plans()
    text = t.NO_PLANS_DEFINED if not plans else t.PLANS_LIST_HEADER
    await message.answer(text, reply_markup=admin_plans_keyboard(plans))


@router.message(F.text == t.ADMIN_MENU_PLANS)
async def show_plans(message: Message):
    await _show_plans(message)


@router.callback_query(F.data == "plan_add")
async def prompt_add_plan(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminPlans.add_name)
    await callback.message.answer(t.ASK_PLAN_NAME)
    await callback.answer()


@router.message(AdminPlans.add_name)
async def set_plan_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(AdminPlans.add_user_count)
    await message.answer(t.ASK_PLAN_USER_COUNT)


def _parse_positive_int(text: str) -> int | None:
    try:
        value = int(text.strip())
        return value if value > 0 else None
    except ValueError:
        return None


@router.message(AdminPlans.add_user_count)
async def set_plan_user_count(message: Message, state: FSMContext):
    value = _parse_positive_int(message.text)
    if value is None:
        await message.answer(t.INVALID_NUMBER)
        return
    await state.update_data(user_count=value)
    await state.set_state(AdminPlans.add_months)
    await message.answer(t.ASK_PLAN_MONTHS)


@router.message(AdminPlans.add_months)
async def set_plan_months(message: Message, state: FSMContext):
    value = _parse_positive_int(message.text)
    if value is None:
        await message.answer(t.INVALID_NUMBER)
        return
    await state.update_data(months=value)
    await state.set_state(AdminPlans.add_traffic_gb)
    await message.answer(t.ASK_PLAN_TRAFFIC)


@router.message(AdminPlans.add_traffic_gb)
async def set_plan_traffic(message: Message, state: FSMContext):
    value = _parse_positive_int(message.text)
    if value is None:
        await message.answer(t.INVALID_NUMBER)
        return
    await state.update_data(traffic_gb=value)
    await state.set_state(AdminPlans.add_price)
    await message.answer(t.ASK_PLAN_PRICE)


@router.message(AdminPlans.add_price)
async def set_plan_price(message: Message, state: FSMContext):
    value = _parse_positive_int(message.text)
    if value is None:
        await message.answer(t.INVALID_NUMBER)
        return
    data = await state.get_data()
    await create_plan(
        name=data["name"],
        user_count=data["user_count"],
        months=data["months"],
        traffic_gb=data["traffic_gb"],
        price=Decimal(value),
    )
    await state.clear()
    await message.answer(t.PLAN_ADDED)
    await _show_plans(message)


@router.callback_query(F.data.startswith("plan_toggle:"))
async def toggle_plan(callback: CallbackQuery):
    plan_id = int(callback.data.split(":")[1])
    await toggle_plan_active(plan_id)
    plans = await list_all_plans()
    await callback.message.edit_text(t.PLAN_TOGGLED, reply_markup=admin_plans_keyboard(plans))
    await callback.answer()


@router.callback_query(F.data.startswith("plan_remove:"))
async def remove_plan_cb(callback: CallbackQuery):
    plan_id = int(callback.data.split(":")[1])
    await remove_plan(plan_id)
    plans = await list_all_plans()
    await callback.message.edit_text(t.PLAN_REMOVED, reply_markup=admin_plans_keyboard(plans))
    await callback.answer()
