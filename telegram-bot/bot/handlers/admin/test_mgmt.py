from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from ... import texts as t
from ...keyboards import (
    admin_menu_keyboard,
    admin_test_keyboard,
    cancel_keyboard,
    wholesaler_test_overrides_keyboard,
    wholesaler_test_override_actions_keyboard,
)
from ...settings_repo import get_setting, set_setting
from ...test_repo import clear_all_test_users, get_test_settings, clear_wholesaler_test_services, clear_all_wholesaler_test_services, count_user_tests
from sqlalchemy import select

from ...db import async_session
from ...models import Wholesaler
from .base import AdminOnlyMiddleware


class AdminTestSettings(StatesGroup):
    edit_traffic = State()
    edit_days = State()
    edit_wholesaler_limit = State()
    set_wholesaler_override = State()


router = Router(name="admin_test")
router.message.middleware(AdminOnlyMiddleware())
router.callback_query.middleware(AdminOnlyMiddleware())


async def _show_test_settings(message: Message):
    settings = await get_test_settings()
    status = "فعال" if settings["enabled"] else "غیرفعال"
    traffic = settings["traffic_gb"]
    traffic_display = f"{traffic:.1f}" if traffic != int(traffic) else str(int(traffic))
    provider_name = "پنل PasarGuard" if settings["provider"] == "panel" else "Xenet API"
    text = (
        f"{t.TEST_SETTINGS_HEADER}\n\n"
        f"وضعیت: {status}\n"
        f"ارائه‌دهنده: {provider_name}\n\n"
        f"📊 تنظیمات پنل:\n"
        f"   ترافیک: {traffic_display} گیگابایت\n"
        f"   مدت: {settings['days']} روز\n\n"
        f"🏷️ سقف تست عمده‌فروشان: {settings['wholesaler_limit']}"
    )
    await message.answer(text, reply_markup=admin_test_keyboard(settings["enabled"], settings["provider"]))


@router.message(F.text == t.ADMIN_MENU_TEST)
async def open_test_menu(message: Message):
    await _show_test_settings(message)


@router.callback_query(F.data == "test_toggle")
async def toggle_test(callback: CallbackQuery):
    settings = await get_test_settings()
    new_value = "0" if settings["enabled"] else "1"
    await set_setting("test_enabled", new_value)
    await callback.answer("وضعیت تغییر کرد")
    await _show_test_settings(callback.message)


@router.callback_query(F.data == "test_edit_wholesaler_limit")
async def prompt_edit_wholesaler_limit(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminTestSettings.edit_wholesaler_limit)
    await callback.message.answer(t.ASK_TEST_WHOLESALER_LIMIT, reply_markup=cancel_keyboard())
    await callback.answer()


@router.message(AdminTestSettings.edit_wholesaler_limit)
async def set_test_wholesaler_limit(message: Message, state: FSMContext):
    try:
        value = int(message.text.strip())
        if value < 0:
            raise ValueError
    except ValueError:
        await message.answer(t.INVALID_NUMBER)
        return
    await set_setting("test_wholesaler_limit", str(value))
    await state.clear()
    await message.answer(t.TEST_SETTINGS_UPDATED)
    await _show_test_settings(message)


@router.callback_query(F.data == "test_wholesaler_overrides")
async def show_wholesaler_overrides(callback: CallbackQuery):
    async with async_session() as session:
        result = await session.execute(
            select(Wholesaler).order_by(Wholesaler.created_at)
        )
        wholesalers = result.scalars().all()
    settings = await get_test_settings()
    text = t.TEST_WHOLESALER_OVERRIDES_HEADER.format(limit=settings["wholesaler_limit"])
    await callback.message.answer(
        text,
        reply_markup=wholesaler_test_overrides_keyboard(wholesalers, settings["wholesaler_limit"]),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("test_wsl_override:" ))
async def show_wholesaler_override_detail(callback: CallbackQuery):
    telegram_id = int(callback.data.split(":")[1])
    async with async_session() as session:
        wholesaler = await session.get(Wholesaler, telegram_id)
    if not wholesaler:
        await callback.answer("عمده‌فروش پیدا نشد", show_alert=True)
        return
    settings = await get_test_settings()
    override = wholesaler.test_limit_override
    display = str(override) if override is not None else f"پیش‌فرض ({settings['wholesaler_limit']})"
    await callback.message.answer(
        t.TEST_WHOLESALER_OVERRIDE_DETAIL.format(
            telegram_id=telegram_id,
            override=display,
            global_limit=settings["wholesaler_limit"],
        ),
        reply_markup=wholesaler_test_override_actions_keyboard(telegram_id, override is not None),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("test_wsl_set:" ))
async def prompt_set_wholesaler_override(callback: CallbackQuery, state: FSMContext):
    telegram_id = int(callback.data.split(":")[1])
    await state.update_data(override_target=telegram_id)
    await state.set_state(AdminTestSettings.set_wholesaler_override)
    await callback.message.answer(
        t.ASK_WHOLESALER_OVERRIDE_LIMIT.format(telegram_id=telegram_id),
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


@router.message(AdminTestSettings.set_wholesaler_override)
async def set_wholesaler_override(message: Message, state: FSMContext):
    data = await state.get_data()
    telegram_id = data["override_target"]
    try:
        value = int(message.text.strip())
        if value < 0:
            raise ValueError
    except ValueError:
        await message.answer(t.INVALID_NUMBER)
        return
    async with async_session() as session:
        wholesaler = await session.get(Wholesaler, telegram_id)
        if wholesaler:
            wholesaler.test_limit_override = value
            await session.commit()
    await state.clear()
    await message.answer(t.WHOLESALER_OVERRIDE_SET.format(telegram_id=telegram_id, limit=value))
    # Show updated detail
    settings = await get_test_settings()
    async with async_session() as session:
        wholesaler = await session.get(Wholesaler, telegram_id)
    if wholesaler:
        await message.answer(
            t.TEST_WHOLESALER_OVERRIDE_DETAIL.format(
                telegram_id=telegram_id,
                override=str(wholesaler.test_limit_override),
                global_limit=settings["wholesaler_limit"],
            ),
            reply_markup=wholesaler_test_override_actions_keyboard(telegram_id, True),
        )


@router.callback_query(F.data.startswith("test_wsl_reset:" ))
async def reset_wholesaler_override(callback: CallbackQuery):
    telegram_id = int(callback.data.split(":")[1])
    async with async_session() as session:
        wholesaler = await session.get(Wholesaler, telegram_id)
        if wholesaler:
            wholesaler.test_limit_override = None
            await session.commit()
    await callback.answer("سقف به حالت پیش‌فرض بازگشت")
    settings = await get_test_settings()
    async with async_session() as session:
        wholesaler = await session.get(Wholesaler, telegram_id)
    if wholesaler:
        await callback.message.edit_text(
            t.TEST_WHOLESALER_OVERRIDE_DETAIL.format(
                telegram_id=telegram_id,
                override=f"پیش‌فرض ({settings['wholesaler_limit']})",
                global_limit=settings["wholesaler_limit"],
            ),
            reply_markup=wholesaler_test_override_actions_keyboard(telegram_id, False),
        )


@router.callback_query(F.data.startswith("test_wsl_clear:"))
async def clear_wholesaler_tests(callback: CallbackQuery):
    telegram_id = int(callback.data.split(":")[1])
    count = await clear_wholesaler_test_services(telegram_id)
    await callback.answer(f"{count} سرویس تست حذف شد")
    await callback.message.answer(t.TEST_WHOLESALER_TESTS_CLEARED.format(count=count, telegram_id=telegram_id))
    # Show updated detail
    settings = await get_test_settings()
    async with async_session() as session:
        wholesaler = await session.get(Wholesaler, telegram_id)
    if wholesaler:
        override = wholesaler.test_limit_override
        display = str(override) if override is not None else f"پیش‌فرض ({settings['wholesaler_limit']})"
        await callback.message.answer(
            t.TEST_WHOLESALER_OVERRIDE_DETAIL.format(
                telegram_id=telegram_id,
                override=display,
                global_limit=settings["wholesaler_limit"],
            ),
            reply_markup=wholesaler_test_override_actions_keyboard(telegram_id, override is not None),
        )


@router.callback_query(F.data == "test_edit_traffic")
async def prompt_edit_traffic(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminTestSettings.edit_traffic)
    await callback.message.answer(t.ASK_TEST_TRAFFIC, reply_markup=cancel_keyboard())
    await callback.answer()


@router.message(AdminTestSettings.edit_traffic)
async def set_test_traffic(message: Message, state: FSMContext):
    try:
        value = float(message.text.strip())
        if value <= 0:
            raise ValueError
    except ValueError:
        await message.answer(t.INVALID_NUMBER)
        return
    await set_setting("test_traffic_gb", str(value))
    await state.clear()
    await message.answer(t.TEST_SETTINGS_UPDATED)
    await _show_test_settings(message)


@router.callback_query(F.data == "test_edit_days")
async def prompt_edit_days(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminTestSettings.edit_days)
    await callback.message.answer(t.ASK_TEST_DAYS, reply_markup=cancel_keyboard())
    await callback.answer()


@router.callback_query(F.data == "test_toggle_provider")
async def toggle_provider(callback: CallbackQuery):
    settings = await get_test_settings()
    new_provider = "xenet" if settings["provider"] == "panel" else "panel"
    await set_setting("test_provider", new_provider)
    await callback.answer("ارائه‌دهنده تغییر کرد")
    await _show_test_settings(callback.message)


@router.message(AdminTestSettings.edit_days)
async def set_test_days(message: Message, state: FSMContext):
    try:
        value = int(message.text.strip())
        if value <= 0:
            raise ValueError
    except ValueError:
        await message.answer(t.INVALID_NUMBER)
        return
    await set_setting("test_days", str(value))
    await state.clear()
    await message.answer(t.TEST_SETTINGS_UPDATED)
    await _show_test_settings(message)


@router.callback_query(F.data == "test_clear_users")
async def clear_test_users(callback: CallbackQuery):
    count = await clear_all_test_users()
    await callback.message.answer(t.TEST_CLEARED.format(count=count))
    await _show_test_settings(callback.message)
    await callback.answer()


@router.callback_query(F.data == "test_clear_wholesaler_tests")
async def clear_all_wholesaler_tests(callback: CallbackQuery):
    count = await clear_all_wholesaler_test_services()
    await callback.message.answer(t.TEST_ALL_WHOLESALER_TESTS_CLEARED.format(count=count))
    await _show_test_settings(callback.message)
    await callback.answer()


@router.callback_query(F.data == "cust_back")
async def back_to_admin(callback: CallbackQuery):
    await callback.message.answer(t.ADMIN_MENU, reply_markup=admin_menu_keyboard())
    await callback.answer()
