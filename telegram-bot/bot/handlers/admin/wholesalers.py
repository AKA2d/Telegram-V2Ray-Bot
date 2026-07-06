import logging
from decimal import Decimal

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from ... import texts as t
from ...keyboards import (
    admin_menu_keyboard,
    admin_wholesalers_keyboard,
    admin_wholesale_plans_keyboard,
    cancel_keyboard,
    wholesaler_plan_action_keyboard,
)
from ...states import AdminWholesalers
from ...wholesalers_repo import (
    assign_wholesale_plan,
    create_wholesaler,
    create_wholesale_plan,
    get_wholesaler_by_telegram_id,
    list_active_wholesale_plans,
    list_assigned_wholesale_plans,
    list_wholesale_plans,
    list_wholesalers,
    remove_wholesaler,
    remove_wholesale_plan,
    toggle_wholesale_plan_active,
    unassign_wholesale_plan,
)
from .base import AdminOnlyMiddleware

router = Router(name="admin_wholesalers")
router.message.middleware(AdminOnlyMiddleware())
router.callback_query.middleware(AdminOnlyMiddleware())

logger = logging.getLogger(__name__)


def _summarize_wholesalers(wholesalers: list) -> str:
    if not wholesalers:
        return t.NO_WHOLESALERS_DEFINED
    lines = ["پلن‌های عمده‌فروشان:"]
    for w in wholesalers:
        lines.append(f"- {w.telegram_id}")
    return "\n".join(lines)


def _summarize_wholesale_plans(plans: list) -> str:
    if not plans:
        return t.NO_WHOLESALE_PLANS_DEFINED
    lines = [t.WHOLESALE_PLANS_LIST_HEADER]
    for p in plans:
        status = "✅" if p.is_active else "🚫"
        lines.append(f"{status} {p.name} — {int(p.price)} تومان")
    return "\n".join(lines)


@router.message(F.text == t.ADMIN_MENU_WHOLESALERS)
async def show_wholesaler_management(message: Message):
    wholesalers = await list_wholesalers()
    plans = await list_wholesale_plans()
    blocks = [t.WHOLESALER_MENU_HEADER, _summarize_wholesalers(wholesalers), "", _summarize_wholesale_plans(plans)]
    await message.answer("\n".join(blocks), reply_markup=admin_wholesalers_keyboard())


@router.callback_query(F.data == "wholesaler_back")
async def back_to_admin(callback: CallbackQuery):
    await callback.message.answer(t.ADMIN_MENU, reply_markup=admin_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "wholesaler_add")
async def prompt_add_wholesaler(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminWholesalers.add_wholesaler)
    await callback.message.answer(t.ASK_WHOLESALER_TELEGRAM_ID, reply_markup=cancel_keyboard())
    await callback.answer()


@router.message(AdminWholesalers.add_wholesaler, F.text)
async def set_wholesaler_id(message: Message, state: FSMContext):
    logger.info("Received wholesaler add input: %s", message.text)
    try:
        telegram_id = int(message.text.strip())
    except ValueError:
        await message.answer(t.INVALID_NUMBER)
        return

    try:
        await create_wholesaler(telegram_id)
    except Exception:
        logger.exception("Failed to create wholesaler for telegram id %s", telegram_id)
        await state.clear()
        await message.answer("ثبت عمده‌فروش با خطا مواجه شد. لطفاً دوباره تلاش کنید.", reply_markup=admin_menu_keyboard())
        return

    await state.clear()
    await message.answer(t.WHOLESALER_ADDED, reply_markup=admin_menu_keyboard())


@router.callback_query(F.data == "wholesaler_remove")
async def prompt_remove_wholesaler(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminWholesalers.remove_wholesaler)
    await callback.message.answer(t.ASK_WHOLESALER_TELEGRAM_ID, reply_markup=cancel_keyboard())
    await callback.answer()


@router.message(AdminWholesalers.remove_wholesaler, F.text)
async def remove_wholesaler_by_id(message: Message, state: FSMContext):
    logger.info("Received wholesaler remove input: %s", message.text)
    try:
        telegram_id = int(message.text.strip())
    except ValueError:
        await message.answer(t.INVALID_NUMBER)
        return

    try:
        await remove_wholesaler(telegram_id)
    except Exception:
        logger.exception("Failed to remove wholesaler for telegram id %s", telegram_id)
        await state.clear()
        await message.answer("حذف عمده‌فروش با خطا مواجه شد. لطفاً دوباره تلاش کنید.", reply_markup=admin_menu_keyboard())
        return

    await state.clear()
    await message.answer(t.WHOLESALER_REMOVED, reply_markup=admin_menu_keyboard())


@router.callback_query(F.data == "wholesale_plan_add")
async def prompt_add_wholesale_plan(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminWholesalers.add_name)
    await callback.message.answer(t.ASK_WHOLESALE_PLAN_NAME, reply_markup=cancel_keyboard())
    await callback.answer()


@router.message(AdminWholesalers.add_name)
async def set_wholesale_plan_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(AdminWholesalers.add_user_count)
    await message.answer(t.ASK_WHOLESALE_PLAN_USER_COUNT)


@router.message(AdminWholesalers.add_user_count)
async def set_wholesale_plan_user_count(message: Message, state: FSMContext):
    try:
        value = int(message.text.strip())
        if value <= 0:
            raise ValueError
    except ValueError:
        await message.answer(t.INVALID_NUMBER)
        return
    await state.update_data(user_count=value)
    await state.set_state(AdminWholesalers.add_months)
    await message.answer(t.ASK_WHOLESALE_PLAN_MONTHS)


@router.message(AdminWholesalers.add_months)
async def set_wholesale_plan_months(message: Message, state: FSMContext):
    try:
        value = int(message.text.strip())
        if value <= 0:
            raise ValueError
    except ValueError:
        await message.answer(t.INVALID_NUMBER)
        return
    await state.update_data(months=value)
    await state.set_state(AdminWholesalers.add_traffic_gb)
    await message.answer(t.ASK_WHOLESALE_PLAN_TRAFFIC)


@router.message(AdminWholesalers.add_traffic_gb)
async def set_wholesale_plan_traffic(message: Message, state: FSMContext):
    try:
        value = int(message.text.strip())
        if value <= 0:
            raise ValueError
    except ValueError:
        await message.answer(t.INVALID_NUMBER)
        return
    await state.update_data(traffic_gb=value)
    await state.set_state(AdminWholesalers.add_price)
    await message.answer(t.ASK_WHOLESALE_PLAN_PRICE)


@router.message(AdminWholesalers.add_price)
async def set_wholesale_plan_price(message: Message, state: FSMContext):
    try:
        value = int(message.text.strip())
        if value <= 0:
            raise ValueError
    except ValueError:
        await message.answer(t.INVALID_NUMBER)
        return

    data = await state.get_data()
    await create_wholesale_plan(
        name=data["name"],
        user_count=data["user_count"],
        months=data["months"],
        traffic_gb=data["traffic_gb"],
        price=Decimal(value),
    )
    await state.clear()
    await message.answer(t.WHOLESALE_PLAN_ADDED, reply_markup=admin_menu_keyboard())


@router.callback_query(F.data == "wholesale_plan_list")
async def show_wholesale_plans(callback: CallbackQuery):
    plans = await list_wholesale_plans()
    await callback.message.answer(
        t.WHOLESALE_PLANS_LIST_HEADER,
        reply_markup=admin_wholesale_plans_keyboard(plans),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("wholesale_plan_toggle:"))
async def toggle_wholesale_plan(callback: CallbackQuery):
    plan_id = int(callback.data.split(":")[1])
    await toggle_wholesale_plan_active(plan_id)
    plans = await list_wholesale_plans()
    await callback.message.edit_text(t.WHOLESALE_PLAN_TOGGLED, reply_markup=admin_wholesale_plans_keyboard(plans))
    await callback.answer()


@router.callback_query(F.data.startswith("wholesale_plan_remove:"))
async def remove_wholesale_plan_cb(callback: CallbackQuery):
    plan_id = int(callback.data.split(":")[1])
    await remove_wholesale_plan(plan_id)
    plans = await list_wholesale_plans()
    await callback.message.edit_text(t.WHOLESALE_PLAN_REMOVED, reply_markup=admin_wholesale_plans_keyboard(plans))
    await callback.answer()


@router.callback_query(F.data == "wholesaler_assign")
async def prompt_assign_wholesaler(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminWholesalers.assign_wholesaler)
    await callback.message.answer(t.ASK_ASSIGN_WHOLESALER_ID, reply_markup=cancel_keyboard())
    await callback.answer()


@router.message(AdminWholesalers.assign_wholesaler, F.text)
async def choose_wholesaler_for_assignment(message: Message, state: FSMContext):
    try:
        telegram_id = int(message.text.strip())
    except ValueError:
        await message.answer(t.INVALID_NUMBER)
        return

    wholesaler = await get_wholesaler_by_telegram_id(telegram_id)
    if not wholesaler:
        await message.answer(t.WHOLESALER_NOT_FOUND)
        return

    plans = await list_active_wholesale_plans()
    if not plans:
        await message.answer(t.NO_WHOLESALE_PLANS_DEFINED, reply_markup=admin_menu_keyboard())
        await state.clear()
        return

    await state.clear()
    await message.answer(
        t.ASSIGN_PLAN_PROMPT,
        reply_markup=wholesaler_plan_action_keyboard(plans, telegram_id, "wholesale_plan_assign"),
    )


@router.callback_query(F.data.startswith("wholesale_plan_assign:"))
async def assign_plan(callback: CallbackQuery):
    _, telegram_id, plan_id = callback.data.split(":")
    await assign_wholesale_plan(int(telegram_id), int(plan_id))
    await callback.message.answer(t.WHOLESALE_PLAN_ASSIGNED, reply_markup=admin_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "wholesaler_unassign")
async def prompt_unassign_wholesaler(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminWholesalers.unassign_wholesaler)
    await callback.message.answer(t.ASK_UNASSIGN_WHOLESALER_ID, reply_markup=cancel_keyboard())
    await callback.answer()


@router.message(AdminWholesalers.unassign_wholesaler, F.text)
async def choose_wholesaler_for_unassignment(message: Message, state: FSMContext):
    try:
        telegram_id = int(message.text.strip())
    except ValueError:
        await message.answer(t.INVALID_NUMBER)
        return

    wholesaler = await get_wholesaler_by_telegram_id(telegram_id)
    if not wholesaler:
        await message.answer(t.WHOLESALER_NOT_FOUND)
        return

    plans = await list_assigned_wholesale_plans(telegram_id)
    if not plans:
        await message.answer(t.NO_WHOLESALE_PLANS_ASSIGNED, reply_markup=admin_menu_keyboard())
        await state.clear()
        return

    await state.clear()
    await message.answer(
        t.UNASSIGN_PLAN_PROMPT,
        reply_markup=wholesaler_plan_action_keyboard(plans, telegram_id, "wholesale_plan_unassign"),
    )


@router.message(F.text)
async def handle_wholesaler_state_text(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return
    if current_state == AdminWholesalers.add_wholesaler.state:
        await set_wholesaler_id(message, state)
        return
    if current_state == AdminWholesalers.remove_wholesaler.state:
        await remove_wholesaler_by_id(message, state)
        return
    if current_state == AdminWholesalers.assign_wholesaler.state:
        await choose_wholesaler_for_assignment(message, state)
        return
    if current_state == AdminWholesalers.unassign_wholesaler.state:
        await choose_wholesaler_for_unassignment(message, state)
        return


@router.callback_query(F.data.startswith("wholesale_plan_unassign:"))
async def unassign_plan(callback: CallbackQuery):
    _, telegram_id, plan_id = callback.data.split(":")
    await unassign_wholesale_plan(int(telegram_id), int(plan_id))
    await callback.message.answer(t.WHOLESALE_PLAN_UNASSIGNED, reply_markup=admin_menu_keyboard())
    await callback.answer()
