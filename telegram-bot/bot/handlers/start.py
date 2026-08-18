import time
import uuid
from datetime import datetime, timedelta, timezone

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import CallbackQuery, Message

from .. import texts as t
from ..config import is_admin, REQUIRED_CHANNEL_ID
from ..keyboards import join_channel_keyboard, main_menu, SUPPORT_USERNAME
from ..membership import is_channel_member
from ..panel_client import PanelAPIError, panel_client
from ..xenet_client import XenetAPIError, xenet_client
from ..services_repo import create_service
from ..test_repo import get_test_settings, has_used_test, mark_test_used
from ..users_repo import get_or_create_user
from ..wholesalers_repo import is_wholesaler

router = Router(name="start")


async def _user_menu(user_id: int):
    return main_menu(is_admin=is_admin(user_id), is_wholesaler=await is_wholesaler(user_id))


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await get_or_create_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    if REQUIRED_CHANNEL_ID and not await is_channel_member(message.bot, message.from_user.id):
        await message.answer(t.JOIN_CHANNEL_PROMPT, reply_markup=join_channel_keyboard(REQUIRED_CHANNEL_ID))
        return
    await message.answer(t.WELCOME, reply_markup=await _user_menu(message.from_user.id))


@router.callback_query(F.data == "check_membership")
async def check_membership(callback: CallbackQuery):
    if await is_channel_member(callback.bot, callback.from_user.id):
        await callback.message.answer(t.WELCOME, reply_markup=await _user_menu(callback.from_user.id))
        await callback.answer()
    else:
        await callback.answer(t.NOT_MEMBER_YET, show_alert=True)


@router.message(F.text == t.BTN_BACK)
async def back_to_main(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(t.WELCOME, reply_markup=await _user_menu(message.from_user.id))


@router.message(default_state, F.text == t.BTN_CANCEL_FLOW)
async def cancel_flow(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(t.CANCELLED, reply_markup=await _user_menu(message.from_user.id))


@router.message(F.text == t.MAIN_MENU_SUPPORT)
async def support(message: Message):
    await message.answer(
        f"برای پشتیبانی با ادمین در تماس باشید:\n@{SUPPORT_USERNAME}",
    )


@router.message(F.text == t.MAIN_MENU_WHOLESALER_STATS)
async def show_wholesaler_stats(message: Message):
    from ..wholesalers_repo import get_wholesaler_stats
    stats = await get_wholesaler_stats(message.from_user.id)
    text = (
        f"📊 آمار شما\n\n"
        f"📦 کل سرویس‌ها: {stats['total_services']}\n"
        f"✅ سرویس‌های فعال: {stats['active_services']}\n"
        f"💰 کل فروش: {stats['total_revenue']:,} تومان\n"
        f"🌐 کل ترافیک: {stats['total_traffic']} گیگ\n"
        f"💳 موجودی کیف پول: {stats['wallet_balance']:,} تومان"
    )
    await message.answer(text, reply_markup=await _user_menu(message.from_user.id))


@router.message(F.text == t.MAIN_MENU_BECOME_WHOLESALER)
async def request_wholesaler(message: Message):
    from ..db import async_session
    from ..models import User
    from ..settings_repo import get_setting
    from ..keyboards import confirm_keyboard

    fee = int(await get_setting("wholesaler_fee"))
    async with async_session() as session:
        user = await session.get(User, message.from_user.id)
        balance = int(user.wallet_balance) if user else 0

    await message.answer(
        t.WHOLESALER_REQUEST_INFO.format(fee=fee, balance=balance),
        reply_markup=confirm_keyboard(),
    )


@router.message(default_state, F.text == t.BTN_CANCEL)
async def cancel_wholesaler_request(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(t.CANCELLED, reply_markup=await _user_menu(message.from_user.id))


@router.message(default_state, F.text == t.BTN_CONFIRM)
async def confirm_wholesaler_request(message: Message):
    from ..db import async_session
    from ..models import User
    from ..settings_repo import get_setting
    from ..wholesalers_repo import is_wholesaler, purchase_wholesaler_membership

    # Check if already a wholesaler
    if await is_wholesaler(message.from_user.id):
        await message.answer("شما از قبل عمده‌فروش هستید.", reply_markup=await _user_menu(message.from_user.id))
        return

    fee = int(await get_setting("wholesaler_fee"))
    async with async_session() as session:
        user = await session.get(User, message.from_user.id)
        balance = int(user.wallet_balance) if user else 0

    if balance >= fee:
        result = await purchase_wholesaler_membership(message.from_user.id, fee)
        if result == "already":
            await message.answer("شما از قبل عمده‌فروش هستید.", reply_markup=await _user_menu(message.from_user.id))
            return
        if result == "insufficient":
            await message.answer(t.WHOLESALER_REQUEST_INSUFFICIENT.format(balance=balance, fee=fee, deficit=fee - balance))
            return

        await message.answer(t.WHOLESALER_REQUEST_ACCEPTED, reply_markup=await _user_menu(message.from_user.id))
    else:
        deficit = fee - balance
        await message.answer(
            t.WHOLESALER_REQUEST_INSUFFICIENT.format(balance=balance, fee=fee, deficit=deficit),
            reply_markup=await _user_menu(message.from_user.id),
        )


@router.message(F.text == t.MAIN_MENU_TEST)
async def get_test_service(message: Message):
    user_id = message.from_user.id
    is_user_admin = is_admin(user_id)

    test_settings = await get_test_settings()
    if not test_settings["enabled"]:
        await message.answer(t.TEST_NOT_AVAILABLE, reply_markup=main_menu(is_user_admin))
        return

    if await has_used_test(user_id):
        await message.answer(t.TEST_ALREADY_USED, reply_markup=main_menu(is_user_admin))
        return

    provider = test_settings["provider"]

    if provider == "xenet":
        # Create test service using Xenet /v2/test endpoint (server-side controlled)
        try:
            xenet_config = await xenet_client.create_v2_test_account()
            subscription_link = xenet_config.sub_link
            xenet_account_id = xenet_config.id
            panel_username = xenet_config.name
        except XenetAPIError as exc:
            await message.answer(t.ERROR_GENERIC, reply_markup=main_menu(is_user_admin))
            return

        # Traffic and duration are controlled server-side by Xenet.
        # Use expire_date from the response if available, otherwise default to 30 days.
        if xenet_config.expire_date:
            try:
                expires_at = datetime.fromisoformat(xenet_config.expire_date)
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
            except ValueError:
                expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        else:
            expires_at = datetime.now(timezone.utc) + timedelta(days=30)

        await create_service(
            owner_telegram_id=user_id,
            service_type="unlimited",
            panel_username=panel_username,
            panel_uuid=None,
            subscription_link=subscription_link,
            status="active",
            user_count=1,
            months=xenet_config.days_left,
            traffic_gb=0,
            price=0,
            expires_at=expires_at,
            xenet_account_id=xenet_account_id,
        )
    else:
        # Create test service using PasarGuard panel
        panel_username = f"test_{user_id}_{uuid.uuid4().hex[:6]}"
        data_limit_bytes = int(test_settings["traffic_gb"] * 1024**3)
        duration_seconds = test_settings["days"] * 86400

        try:
            panel_user = await panel_client.create_active_user(
                username=panel_username,
                data_limit_bytes=data_limit_bytes,
                duration_seconds=duration_seconds,
            )
        except PanelAPIError as exc:
            await message.answer(t.ERROR_GENERIC, reply_markup=main_menu(is_user_admin))
            return

        subscription_link = panel_user.subscription_link
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=duration_seconds)
        await create_service(
            owner_telegram_id=user_id,
            service_type="traffic_based",
            panel_username=panel_user.username,
            panel_uuid=panel_user.uuid,
            subscription_link=subscription_link,
            status="active",
            user_count=1,
            months=test_settings["days"],
            traffic_gb=test_settings["traffic_gb"],
            price=0,
            expires_at=expires_at,
        )

    await mark_test_used(user_id)

    from ..qr_gen import generate_qr_image
    if provider == "xenet":
        traffic_text = "نامحدود"
        plan_name = "تست رایگان"
        days_display = xenet_config.days_left * 30 if xenet_config.days_left else 30
    else:
        traffic_text = f"{test_settings['traffic_gb']} گیگابایت"
        plan_name = "تست رایگان"
        days_display = test_settings["days"] * 30
    text = t.SERVICE_ACTIVATED_DETAILED.format(
        username=panel_username,
        plan_name=plan_name,
        price="رایگان",
        months=days_display,
        traffic=traffic_text,
        link=subscription_link or "—",
    )
    if subscription_link:
        qr_photo = generate_qr_image(subscription_link)
        await message.answer_photo(qr_photo, caption=text, reply_markup=main_menu(is_user_admin))
    else:
        await message.answer(text, reply_markup=main_menu(is_user_admin))
    await message.answer(t.POST_PURCHASE_HINT)
