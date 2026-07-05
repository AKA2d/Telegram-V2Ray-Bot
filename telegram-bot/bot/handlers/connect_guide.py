from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from .. import texts as t
from ..keyboards import connect_apps_keyboard, connect_platform_keyboard, CONNECT_APPS
from ..states import ConnectGuide

router = Router(name="connect_guide")

GUIDE_TEXT = {
    ("ios", "Streisand"): "1. اپلیکیشن Streisand را از App Store نصب کنید.\n2. لینک اشتراک را کپی کنید.\n3. داخل اپ گزینه Add Config from Clipboard را بزنید.\n4. اتصال را برقرار کنید.",
    ("ios", "FoXray"): "1. اپلیکیشن FoXray را از App Store نصب کنید.\n2. لینک اشتراک را وارد کنید.\n3. سرور را انتخاب و متصل شوید.",
    ("ios", "V2Box"): "1. اپلیکیشن V2Box را نصب کنید.\n2. لینک را از طریق Import from Clipboard اضافه کنید.\n3. متصل شوید.",
    ("android", "v2rayNG"): "1. اپلیکیشن v2rayNG را از Google Play یا سایت نصب کنید.\n2. لینک اشتراک را کپی کنید.\n3. از منو گزینه Import config from Clipboard را بزنید.\n4. متصل شوید.",
    ("android", "NapsternetV"): "1. اپلیکیشن NapsternetV را نصب کنید.\n2. لینک را وارد کنید.\n3. سرور را انتخاب و متصل شوید.",
    ("android", "Hiddify"): "1. اپلیکیشن Hiddify را نصب کنید.\n2. لینک اشتراک را اضافه کنید.\n3. متصل شوید.",
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
