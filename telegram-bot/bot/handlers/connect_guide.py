from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from .. import texts as t
from ..keyboards import connect_apps_keyboard, connect_platform_keyboard, CONNECT_APPS
from ..states import ConnectGuide

router = Router(name="connect_guide")

GUIDE_TEXT = {
    ("ios", "v2box"): "راهنمای اتصال با v2box:\nhttps://t.me/GodVPN_Guide/125",
    ("ios", "NapsternetV"): "راهنمای اتصال با NapsternetV:\nhttps://t.me/GodVPN_Guide/124",
    ("android", "v2rayNG"): "راهنمای اتصال با v2rayNG:\nhttps://t.me/GodVPN_Guide/122",
    ("android", "NapsternetV"): "راهنمای اتصال با NapsternetV:\nhttps://t.me/GodVPN_Guide/124",
    ("android", "v2box"): "راهنمای اتصال با v2box:\nhttps://t.me/GodVPN_Guide/125",
    ("windows", "v2rayN"): (
        "راهنمای اتصال با v2rayN:\n\n"
        "1. دانلود v2rayN از:\n"
        "https://github.com/2dust/v2rayN/releases/latest\n\n"
        "2. فایل zip را اکسترact کنید و v2rayN.exe را اجرا کنید\n\n"
        "3. روی آیکون v2rayN در system tray کلیک راست کنید\n\n"
        "4. گزینه اضافه کردن لینک سابسکریپشن را بزنید\n\n"
        "5. لینک اشتراک خود را پیست کنید\n\n"
        "6. سرور را انتخاب کنید و اتصال را بزنید"
    ),
    ("windows", "Hiddify"): (
        "راهنمای اتصال با Hiddify:\n\n"
        "1. دانلود Hiddify از:\n"
        "https://github.com/hiddify/hiddify-app/releases/latest\n\n"
        "2. نصب و اجرای برنامه\n\n"
        "3. لینک اشتراک را کپی کنید\n\n"
        "4. در برنامه لینک را پیست و اضافه کنید\n\n"
        "5. اتصال را بزنید"
    ),
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
    guide = GUIDE_TEXT.get((platform, app_name), "راهنما به‌زودی اضافه می‌شود.")
    await message.answer(guide)
