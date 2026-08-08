from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from ... import texts as t
from ...keyboards import admin_menu_keyboard, admin_test_keyboard, cancel_keyboard
from ...settings_repo import get_setting, set_setting
from ...test_repo import clear_all_test_users, get_test_settings
from .base import AdminOnlyMiddleware


class AdminTestSettings(StatesGroup):
    edit_traffic = State()
    edit_days = State()
    edit_xenet_traffic = State()
    edit_xenet_days = State()


router = Router(name="admin_test")
router.message.middleware(AdminOnlyMiddleware())
router.callback_query.middleware(AdminOnlyMiddleware())


async def _show_test_settings(message: Message):
    settings = await get_test_settings()
    status = "فعال" if settings["enabled"] else "غیرفعال"
    traffic = settings["traffic_gb"]
    traffic_display = f"{traffic:.1f}" if traffic != int(traffic) else str(int(traffic))
    provider_name = "پنل PasarGuard" if settings["provider"] == "panel" else "Xenet API"
    xenet_traffic = settings["xenet_traffic_gb"]
    xenet_traffic_display = f"{xenet_traffic:.1f}" if xenet_traffic != int(xenet_traffic) else str(int(xenet_traffic))
    text = (
        f"{t.TEST_SETTINGS_HEADER}\n\n"
        f"وضعیت: {status}\n"
        f"ارائه‌دهنده: {provider_name}\n\n"
        f"📊 تنظیمات پنل:\n"
        f"   ترافیک: {traffic_display} گیگابایت\n"
        f"   مدت: {settings['days']} روز\n\n"
        f"♾️ تنظیمات Xenet:\n"
        f"   ترافیک: {xenet_traffic_display} گیگابایت\n"
        f"   مدت: {settings['xenet_days']} روز"
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


@router.callback_query(F.data == "test_edit_xenet_traffic")
async def prompt_edit_xenet_traffic(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminTestSettings.edit_xenet_traffic)
    await callback.message.answer(t.ASK_TEST_XENET_TRAFFIC, reply_markup=cancel_keyboard())
    await callback.answer()


@router.message(AdminTestSettings.edit_xenet_traffic)
async def set_test_xenet_traffic(message: Message, state: FSMContext):
    try:
        value = float(message.text.strip())
        if value <= 0:
            raise ValueError
    except ValueError:
        await message.answer(t.INVALID_NUMBER)
        return
    await set_setting("test_xenet_traffic_gb", str(value))
    await state.clear()
    await message.answer(t.TEST_SETTINGS_UPDATED)
    await _show_test_settings(message)


@router.callback_query(F.data == "test_edit_xenet_days")
async def prompt_edit_xenet_days(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminTestSettings.edit_xenet_days)
    await callback.message.answer(t.ASK_TEST_XENET_DAYS, reply_markup=cancel_keyboard())
    await callback.answer()


@router.message(AdminTestSettings.edit_xenet_days)
async def set_test_xenet_days(message: Message, state: FSMContext):
    try:
        value = int(message.text.strip())
        if value <= 0:
            raise ValueError
    except ValueError:
        await message.answer(t.INVALID_NUMBER)
        return
    await set_setting("test_xenet_days", str(value))
    await state.clear()
    await message.answer(t.TEST_SETTINGS_UPDATED)
    await _show_test_settings(message)


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


@router.callback_query(F.data == "cust_back")
async def back_to_admin(callback: CallbackQuery):
    await callback.message.answer(t.ADMIN_MENU, reply_markup=admin_menu_keyboard())
    await callback.answer()
