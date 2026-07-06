from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from .. import texts as t
from ..keyboards import connect_apps_keyboard, connect_platform_keyboard, CONNECT_APPS
from ..states import ConnectGuide

router = Router(name="connect_guide")

GUIDE_TEXT = {
    ("ios", "NapsternetV"): "https://t.me/GodVPN_Guide/124",
    ("ios", "HAPP"): "https://t.me/GodVPN_Guide/121",
    ("android", "v2rayNG"): "https://t.me/GodVPN_Guide/122",
    ("android", "NapsternetV"): "https://t.me/GodVPN_Guide/124",
    ("android", "HAPP"): "https://t.me/GodVPN_Guide/121",
}


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


@router.message(ConnectGuide.app)
async def choose_app(message: Message, state: FSMContext):
    data = await state.get_data()
    platform = data.get("platform", "android")
    app_name = message.text.split(" ⭐️")[0].strip()
    valid_names = {name for name, _ in CONNECT_APPS.get(platform, [])}
    if app_name not in valid_names:
        return
    guide = GUIDE_TEXT.get((platform, app_name), "راهنما به‌زودی اضافه می‌شود.")
    await message.answer(guide)
