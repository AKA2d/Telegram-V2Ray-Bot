"""Admin guide management."""

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
    choose_guide = State()
    edit_text = State()


PLATFORM_APPS = {
    "ios": [("v2box", "iOS - v2box"), ("NapsternetV", "iOS - NapsternetV")],
    "android": [("v2rayNG", "Android - v2rayNG"), ("v2box", "Android - v2box"), ("NapsternetV", "Android - NapsternetV")],
    "windows": [("v2rayN", "Windows - v2rayN"), ("Nekoray", "Windows - Nekoray"), ("Hiddify", "Windows - Hiddify")],
}


def _all_guides_flat():
    """Return flat list of (key, label) for all guides."""
    result = []
    for platform, apps in PLATFORM_APPS.items():
        for app_key, label in apps:
            result.append((f"guide_{platform}_{app_key}", label))
    return result


@router.message(F.text == "📖 مدیریت راهنماها")
async def open_guide_menu(message: Message):
    if not is_admin(message.from_user.id):
        return
    from ...keyboards import admin_guide_keyboard
    await message.answer("راهنمای مورد نظر را برای ویرایش انتخاب کنید:", reply_markup=admin_guide_keyboard())


@router.callback_query(F.data == "guide_list")
async def show_guide_list(callback: CallbackQuery):
    guides = _all_guides_flat()
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
