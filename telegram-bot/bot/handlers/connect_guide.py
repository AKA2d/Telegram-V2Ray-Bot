from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from .. import texts as t
from ..keyboards import connect_apps_keyboard, connect_platform_keyboard, CONNECT_APPS
from ..settings_repo import get_setting
from ..states import ConnectGuide

router = Router(name="connect_guide")


async def _get_guide(platform: str, app_name: str) -> str:
    """Load guide from admin_settings or return default."""
    key = f"guide_{platform}_{app_name}"
    guide = await get_setting(key)
    if guide and guide.strip():
        return guide
    return "راهنما به‌زودی اضافه می‌شود."


@router.message(F.text == t.MAIN_MENU_CONNECT)
async def connect_start(message: Message, state: FSMContext):
    await state.set_state(ConnectGuide.platform)
    await message.answer(t.CONNECT_CHOOSE_PLATFORM, reply_markup=connect_platform_keyboard())


@router.message(ConnectGuide.platform, F.text == t.CONNECT_PLATFORM_IOS)
async def choose_ios(message: Message, state: FSMContext):
    await state.update_data(platform="ios")
    await state.set_state(ConnectGuide.app)
    await message.answer(t.CONNECT_CHOOSE_APP, reply_markup=connect_apps_keyboard("ios"))


@router.message(ConnectGuide.platform, F.text == t.CONNECT_PLATFORM_ANDROID)
async def choose_android(message: Message, state: FSMContext):
    await state.update_data(platform="android")
    await state.set_state(ConnectGuide.app)
    await message.answer(t.CONNECT_CHOOSE_APP, reply_markup=connect_apps_keyboard("android"))


@router.message(ConnectGuide.platform, F.text == t.CONNECT_PLATFORM_WINDOWS)
async def choose_windows(message: Message, state: FSMContext):
    await state.update_data(platform="windows")
    await state.set_state(ConnectGuide.app)
    await message.answer(t.CONNECT_CHOOSE_APP, reply_markup=connect_apps_keyboard("windows"))


@router.message(ConnectGuide.app)
async def choose_app(message: Message, state: FSMContext):
    data = await state.get_data()
    platform = data.get("platform", "android")
    app_name = message.text.split(" ⭐️")[0].strip()
    valid_names = {name for name, _ in CONNECT_APPS.get(platform, [])}
    if app_name not in valid_names:
        return
    guide = await _get_guide(platform, app_name)
    await message.answer(guide)
