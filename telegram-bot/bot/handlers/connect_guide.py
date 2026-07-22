from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from .. import texts as t
from ..keyboards import connect_platform_keyboard
from ..settings_repo import get_setting
from ..states import ConnectGuide

router = Router(name="connect_guide")


async def _get_guide(platform: str, app_key: str) -> str:
    """Load guide from admin_settings or return default."""
    key = f"guide_{platform}_{app_key}"
    guide = await get_setting(key)
    if guide and guide.strip():
        return guide
    return "راهنما به‌زودی اضافه می‌شود."


async def _get_platform_apps(platform: str) -> list:
    """Load apps for a platform from database."""
    from ..handlers.admin.guide_mgmt import get_platform_apps
    apps = await get_platform_apps()
    return apps.get(platform, [])


async def _connect_apps_keyboard(platform: str):
    """Build apps keyboard from database."""
    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
    apps = await _get_platform_apps(platform)
    rows = []
    for app in apps:
        label = f"{app['label']} ⭐️ پیشنهاد ما" if app.get("recommended") else app["label"]
        rows.append([KeyboardButton(text=label)])
    rows.append([KeyboardButton(text=t.BTN_BACK)])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


@router.message(F.text == t.MAIN_MENU_CONNECT)
async def connect_start(message: Message, state: FSMContext):
    await state.set_state(ConnectGuide.platform)
    await message.answer(t.CONNECT_CHOOSE_PLATFORM, reply_markup=connect_platform_keyboard())


@router.message(ConnectGuide.platform, F.text == t.CONNECT_PLATFORM_IOS)
async def choose_ios(message: Message, state: FSMContext):
    await state.update_data(platform="ios")
    await state.set_state(ConnectGuide.app)
    keyboard = await _connect_apps_keyboard("ios")
    await message.answer(t.CONNECT_CHOOSE_APP, reply_markup=keyboard)


@router.message(ConnectGuide.platform, F.text == t.CONNECT_PLATFORM_ANDROID)
async def choose_android(message: Message, state: FSMContext):
    await state.update_data(platform="android")
    await state.set_state(ConnectGuide.app)
    keyboard = await _connect_apps_keyboard("android")
    await message.answer(t.CONNECT_CHOOSE_APP, reply_markup=keyboard)


@router.message(ConnectGuide.platform, F.text == t.CONNECT_PLATFORM_WINDOWS)
async def choose_windows(message: Message, state: FSMContext):
    await state.update_data(platform="windows")
    await state.set_state(ConnectGuide.app)
    keyboard = await _connect_apps_keyboard("windows")
    await message.answer(t.CONNECT_CHOOSE_APP, reply_markup=keyboard)


@router.message(ConnectGuide.app)
async def choose_app(message: Message, state: FSMContext):
    data = await state.get_data()
    platform = data.get("platform", "android")
    app_name = message.text.split(" ⭐️")[0].strip()

    apps = await _get_platform_apps(platform)
    app_keys = {a["label"]: a["key"] for a in apps}
    if app_name not in app_keys:
        return

    app_key = app_keys[app_name]
    guide = await _get_guide(platform, app_key)
    await message.answer(guide)
