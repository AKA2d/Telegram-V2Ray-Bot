import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from ... import texts as t
from ...keyboards import admin_menu_keyboard, admin_wholesalers_keyboard, cancel_keyboard, wholesaler_stats_keyboard
from ...states import AdminWholesalers
from ...wholesalers_repo import (
    create_wholesaler,
    get_all_wholesalers_stats,
    get_wholesaler_stats,
    list_wholesalers,
    remove_wholesaler,
)
from .base import AdminOnlyMiddleware

router = Router(name="admin_wholesalers")
router.message.middleware(AdminOnlyMiddleware())
router.callback_query.middleware(AdminOnlyMiddleware())

logger = logging.getLogger(__name__)


def _summarize_wholesalers(wholesalers: list) -> str:
    if not wholesalers:
        return t.NO_WHOLESALERS_DEFINED
    lines = ["عمده‌فروشان:"]
    for w in wholesalers:
        lines.append(f"- {w.telegram_id}")
    return "\n".join(lines)


@router.message(F.text == t.ADMIN_MENU_WHOLESALERS)
async def show_wholesaler_management(message: Message):
    wholesalers = await list_wholesalers()
    blocks = [t.WHOLESALER_MENU_HEADER, _summarize_wholesalers(wholesalers)]
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


@router.callback_query(F.data == "wholesaler_stats")
async def show_wholesaler_stats(callback: CallbackQuery):
    wholesalers = await list_wholesalers()
    if not wholesalers:
        await callback.answer(t.NO_WHOLESALERS_DEFINED, show_alert=True)
        return

    bulk = await get_all_wholesalers_stats()
    text = (
        f"📊 آمار کلی عمده‌فروشان\n\n"
        f"👥 تعداد عمده‌فروشان: {bulk['count']}\n"
        f"📦 کل سرویس‌ها: {bulk['total_services']}\n"
        f"✅ سرویس‌های فعال: {bulk['active_services']}\n"
        f"💰 کل فروش: {bulk['total_revenue']:,} تومان\n"
        f"🌐 کل ترافیک: {bulk['total_traffic']} گیگ\n"
        f"💳 کل موجودی کیف پول: {bulk['total_wallet']:,} تومان\n\n"
        f"برای دیدن جزئیات هر عمده‌فروش، روی آیدی او کلیک کنید:"
    )
    await callback.message.edit_text(text, reply_markup=wholesaler_stats_keyboard(wholesalers))
    await callback.answer()


@router.callback_query(F.data.startswith("wholesaler_detail:"))
async def show_wholesaler_detail(callback: CallbackQuery):
    telegram_id = int(callback.data.split(":")[1])
    stats = await get_wholesaler_stats(telegram_id)
    text = (
        f"📊 آمار عمده‌فروش {telegram_id}\n\n"
        f"📦 کل سرویس‌ها: {stats['total_services']}\n"
        f"✅ سرویس‌های فعال: {stats['active_services']}\n"
        f"💰 کل فروش: {stats['total_revenue']:,} تومان\n"
        f"🌐 کل ترافیک: {stats['total_traffic']} گیگ\n"
        f"💳 موجودی کیف پول: {stats['wallet_balance']:,} تومان"
    )
    await callback.message.edit_text(text)
    await callback.answer()


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
