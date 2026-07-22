"""Admin guide management."""

import json

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from ... import texts as t
from ...config import is_admin
from ...keyboards import admin_menu_keyboard, cancel_keyboard
from ...settings_repo import get_setting, set_setting
from .base import AdminOnlyMiddleware

router = Router(name="admin_guides")
router.message.middleware(AdminOnlyMiddleware())
router.callback_query.middleware(AdminOnlyMiddleware())


class EditGuide(StatesGroup):
    edit_text = State()


class AddApp(StatesGroup):
    platform = State()
    app_name = State()


DEFAULT_PLATFORM_APPS = {
    "ios": [{"key": "v2box", "label": "v2box", "recommended": True}, {"key": "NapsternetV", "label": "NapsternetV", "recommended": False}],
    "android": [{"key": "v2rayNG", "label": "v2rayNG", "recommended": True}, {"key": "v2box", "label": "v2box", "recommended": True}, {"key": "NapsternetV", "label": "NapsternetV", "recommended": False}],
    "windows": [{"key": "v2rayN", "label": "v2rayN", "recommended": True}, {"key": "Nekoray", "label": "Nekoray", "recommended": False}, {"key": "Hiddify", "label": "Hiddify", "recommended": False}],
}


async def get_platform_apps() -> dict:
    """Load platform apps from database or use defaults."""
    raw = await get_setting("platform_apps")
    if raw and raw.strip() and raw.strip() not in ("0", ""):
        try:
            result = json.loads(raw)
            if isinstance(result, dict):
                return result
        except (json.JSONDecodeError, ValueError):
            pass
    return DEFAULT_PLATFORM_APPS


async def save_platform_apps(apps: dict) -> None:
    await set_setting("platform_apps", json.dumps(apps))


async def _all_guides_flat():
    """Return flat list of (key, label) for all guides."""
    apps = await get_platform_apps()
    result = []
    for platform, app_list in apps.items():
        for app in app_list:
            result.append((f"guide_{platform}_{app['key']}", f"{platform.title()} - {app['label']}"))
    return result





@router.callback_query(F.data == "guide_list")
async def show_guide_list(callback: CallbackQuery):
    guides = await _all_guides_flat()
    from ...keyboards import guide_list_keyboard
    await callback.message.edit_text("راهنمای مورد نظر را برای ویرایش انتخاب کنید:", reply_markup=guide_list_keyboard(guides))
    await callback.answer()


@router.callback_query(F.data.startswith("guide_edit:"))
async def prompt_edit_guide(callback: CallbackQuery, state: FSMContext):
    guide_key = callback.data.split(":", 1)[1]
    current = await get_setting(guide_key)
    await state.update_data(guide_key=guide_key)
    await state.set_state(EditGuide.edit_text)
    guide_name = guide_key.replace("guide_", "").replace("_", " ").title()
    text = f"ویرایش راهنما: {guide_name}\n\nمتن فعلی:\n{current or '(خالی)'}\n\nمتن جدید را ارسال کنید:"
    await callback.message.edit_text(text)
    await callback.answer()


@router.message(EditGuide.edit_text)
async def save_guide(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    guide_key = data["guide_key"]
    await set_setting(guide_key, message.text)
    await state.clear()
    await message.answer("راهنما با موفقیت ذخیره شد.", reply_markup=admin_menu_keyboard())


@router.callback_query(F.data == "guide_add_app")
async def prompt_add_app(callback: CallbackQuery, state: FSMContext):
    from ...keyboards import platform_choice_keyboard
    await state.set_state(AddApp.platform)
    await callback.message.edit_text("پلتفرم را انتخاب کنید:", reply_markup=platform_choice_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("guide_add_app_platform:"))
async def choose_platform_for_add(callback: CallbackQuery, state: FSMContext):
    platform = callback.data.split(":")[1]
    await state.update_data(platform=platform)
    await state.set_state(AddApp.app_name)
    await callback.message.edit_text(f"نام اپلیکیشن را وارد کنید (مثلا v2rayN):")
    await callback.answer()


@router.message(AddApp.app_name)
async def add_app(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    platform = data["platform"]
    app_name = message.text.strip()
    app_key = app_name.replace(" ", "")

    apps = await get_platform_apps()
    if platform not in apps:
        apps[platform] = []

    existing_keys = [a["key"] for a in apps[platform]]
    if app_key in existing_keys:
        await state.clear()
        await message.answer("این اپلیکیشن قبلاً اضافه شده است.", reply_markup=admin_menu_keyboard())
        return

    apps[platform].append({"key": app_key, "label": app_name, "recommended": False})
    await save_platform_apps(apps)
    await state.clear()
    await message.answer(f"اپلیکیشن {app_name} به پلتفرم {platform} اضافه شد.", reply_markup=admin_menu_keyboard())


@router.callback_query(F.data == "guide_remove_app")
async def prompt_remove_app(callback: CallbackQuery):
    from ...keyboards import remove_app_keyboard
    apps = await get_platform_apps()
    await callback.message.edit_text("اپلیکیشن مورد نظر برای حذف را انتخاب کنید:", reply_markup=remove_app_keyboard(apps))
    await callback.answer()


@router.callback_query(F.data.startswith("guide_remove_app_confirm:"))
async def remove_app(callback: CallbackQuery):
    _, platform, app_key = callback.data.split(":")
    apps = await get_platform_apps()
    if platform in apps:
        apps[platform] = [a for a in apps[platform] if a["key"] != app_key]
        await save_platform_apps(apps)

    await set_setting(f"guide_{platform}_{app_key}", "")

    await callback.answer("اپلیکیشن حذف شد.", show_alert=True)
    from ...keyboards import guide_management_keyboard
    await callback.message.edit_text("مدیریت راهنماها:", reply_markup=guide_management_keyboard())


@router.callback_query(F.data == "guide_back")
async def back_to_guide_menu(callback: CallbackQuery):
    from ...keyboards import guide_management_keyboard
    await callback.message.edit_text("مدیریت راهنماها:", reply_markup=guide_management_keyboard())
    await callback.answer()
