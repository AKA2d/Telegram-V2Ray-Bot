from decimal import Decimal

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from ... import texts as t
from ...keyboards import admin_plans_keyboard, format_admin_plans_list, plan_edit_field_keyboard, service_type_keyboard
from ...plans_repo import create_plan, get_plan, list_all_plans, remove_plan, toggle_plan_active, update_plan_field
from ...states import AdminPlans
from .base import AdminOnlyMiddleware

router = Router(name="admin_plans")
router.message.middleware(AdminOnlyMiddleware())
router.callback_query.middleware(AdminOnlyMiddleware())


async def _show_plans(message: Message):
    plans = await list_all_plans()
    await message.answer(format_admin_plans_list(plans), reply_markup=admin_plans_keyboard(plans))


@router.message(F.text == t.ADMIN_MENU_PLANS)
async def show_plans(message: Message):
    await _show_plans(message)


@router.callback_query(F.data == "plan_add")
async def prompt_add_plan(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminPlans.add_service_type)
    await callback.message.answer("نوع سرویس را انتخاب کنید:", reply_markup=service_type_keyboard())
    await callback.answer()


@router.callback_query(AdminPlans.add_service_type, F.data.startswith("service_type:"))
async def set_plan_service_type(callback: CallbackQuery, state: FSMContext):
    service_type = callback.data.split(":")[1]
    await state.update_data(service_type=service_type)
    await state.set_state(AdminPlans.add_name)
    await callback.message.answer(t.ASK_PLAN_NAME)
    await callback.answer()


@router.message(AdminPlans.add_name)
async def set_plan_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    data = await state.get_data()
    service_type = data.get("service_type", "traffic_based")
    
    if service_type == "unlimited":
        # Unlimited plans: skip user_count (fixed at 1) and traffic_gb
        await state.update_data(user_count=1, traffic_gb=0)
        await state.set_state(AdminPlans.add_months)
        await message.answer(t.ASK_PLAN_MONTHS)
    else:
        # Traffic-based plans: ask for user_count as usual
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
    data = await state.get_data()
    service_type = data.get("service_type", "traffic_based")
    
    if service_type == "unlimited":
        # Unlimited plans: skip traffic_gb, go directly to price
        await state.set_state(AdminPlans.add_price)
        await message.answer(t.ASK_PLAN_PRICE)
    else:
        # Traffic-based plans: ask for traffic_gb
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
    await state.update_data(price=Decimal(value))
    await state.set_state(AdminPlans.add_wholesale_price)
    await message.answer(t.ASK_PLAN_WHOLESALE_PRICE)


@router.message(AdminPlans.add_wholesale_price)
async def set_plan_wholesale_price(message: Message, state: FSMContext):
    text = message.text.strip()
    # Allow empty/skip to use null (same as normal price)
    if text in ("", "-", "0", "skip"):
        wholesale_price = None
    else:
        value = _parse_positive_int(text)
        if value is None:
            await message.answer(t.INVALID_NUMBER)
            return
        wholesale_price = Decimal(value)

    data = await state.get_data()
    await create_plan(
        name=data["name"],
        service_type=data.get("service_type", "traffic_based"),
        user_count=data["user_count"],
        months=data["months"],
        traffic_gb=data["traffic_gb"],
        price=data["price"],
        wholesale_price=wholesale_price,
    )
    await state.clear()
    await message.answer(t.PLAN_ADDED)
    await _show_plans(message)


@router.callback_query(F.data.startswith("plan_toggle:"))
async def toggle_plan(callback: CallbackQuery):
    plan_id = int(callback.data.split(":")[1])
    plan = await get_plan(plan_id)
    if not plan:
        await callback.answer(t.PLAN_NOT_FOUND, show_alert=True)
        return
    from ...keyboards import InlineKeyboardButton, InlineKeyboardMarkup
    new_status = "غیرفعال" if plan.is_active else "فعال"
    await callback.message.edit_text(
        f"آیا مطمئن هستید که می‌خواهید وضعیت پلن «{plan.name}» را به {new_status} تغییر دهید?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t.CONFIRM_YES, callback_data=f"plan_toggle_confirm:{plan_id}")],
            [InlineKeyboardButton(text=t.CONFIRM_NO, callback_data="plan_edit_cancel")],
        ]),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("plan_toggle_confirm:"))
async def confirm_toggle_plan(callback: CallbackQuery):
    plan_id = int(callback.data.split(":")[1])
    await toggle_plan_active(plan_id)
    plans = await list_all_plans()
    await callback.message.edit_text(format_admin_plans_list(plans), reply_markup=admin_plans_keyboard(plans))
    await callback.answer()


@router.callback_query(F.data.startswith("plan_remove:"))
async def remove_plan_cb(callback: CallbackQuery):
    plan_id = int(callback.data.split(":")[1])
    plan = await get_plan(plan_id)
    if not plan:
        await callback.answer(t.PLAN_NOT_FOUND, show_alert=True)
        return
    from ...keyboards import InlineKeyboardButton, InlineKeyboardMarkup
    await callback.message.edit_text(
        f"⚠️ آیا مطمئن هستید که می‌خواهید پلن «{plan.name}» را حذف کنید?\n\nاین عمل غیرقابل بازگشت است.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t.CONFIRM_YES, callback_data=f"plan_remove_confirm:{plan_id}")],
            [InlineKeyboardButton(text=t.CONFIRM_NO, callback_data="plan_edit_cancel")],
        ]),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("plan_remove_confirm:"))
async def confirm_remove_plan(callback: CallbackQuery):
    plan_id = int(callback.data.split(":")[1])
    await remove_plan(plan_id)
    plans = await list_all_plans()
    await callback.message.edit_text(format_admin_plans_list(plans), reply_markup=admin_plans_keyboard(plans))
    await callback.answer()


@router.callback_query(F.data.startswith("plan_edit:"))
async def prompt_edit_plan(callback: CallbackQuery, state: FSMContext):
    plan_id = int(callback.data.split(":")[1])
    plan = await get_plan(plan_id)
    if not plan:
        await callback.answer(t.PLAN_NOT_FOUND, show_alert=True)
        return
    await state.update_data(plan_id=plan_id)
    await state.set_state(AdminPlans.edit_field)
    await callback.message.edit_text(
        t.PLAN_EDIT_CHOOSE_FIELD.format(name=plan.name),
        reply_markup=plan_edit_field_keyboard(plan_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("plan_edit_field:"))
async def choose_edit_field(callback: CallbackQuery, state: FSMContext):
    _, plan_id, field = callback.data.split(":")
    await state.update_data(edit_field=field)
    await state.set_state(AdminPlans.edit_value)
    prompts = {
        "name": t.PLAN_EDIT_NAME,
        "user_count": t.PLAN_EDIT_USER_COUNT,
        "months": t.PLAN_EDIT_MONTHS,
        "traffic_gb": t.PLAN_EDIT_TRAFFIC,
        "price": t.PLAN_EDIT_PRICE,
        "wholesale_price": t.PLAN_EDIT_WHOLESALE_PRICE,
    }
    await callback.message.edit_text(prompts.get(field, "مقدار جدید را وارد کنید:"))
    await callback.answer()


@router.callback_query(F.data == "plan_edit_cancel")
async def cancel_edit(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    plans = await list_all_plans()
    await callback.message.edit_text(format_admin_plans_list(plans), reply_markup=admin_plans_keyboard(plans))
    await callback.answer()


@router.message(AdminPlans.edit_value)
async def set_edited_value(message: Message, state: FSMContext):
    data = await state.get_data()
    plan_id = data["plan_id"]
    field = data["edit_field"]
    text = message.text.strip()

    int_fields = {"user_count", "months", "traffic_gb", "price"}
    if field in int_fields:
        if field == "wholesale_price":
            if text in ("", "-", "0", "skip"):
                value = None
            else:
                value = _parse_positive_int(text)
                if value is None:
                    await message.answer(t.INVALID_NUMBER)
                    return
                value = Decimal(value)
        else:
            value = _parse_positive_int(text)
            if value is None:
                await message.answer(t.INVALID_NUMBER)
                return
            if field == "price":
                value = Decimal(value)
    elif field == "wholesale_price":
        if text in ("", "-", "0", "skip"):
            value = None
        else:
            v = _parse_positive_int(text)
            if v is None:
                await message.answer(t.INVALID_NUMBER)
                return
            value = Decimal(v)
    elif field == "name":
        value = text
    else:
        value = text

    await update_plan_field(plan_id, **{field: value})
    await state.clear()
    await message.answer(t.PLAN_FIELD_UPDATED)
    plans = await list_all_plans()
    await message.answer(format_admin_plans_list(plans), reply_markup=admin_plans_keyboard(plans))
