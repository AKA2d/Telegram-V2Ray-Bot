import logging
import uuid
from decimal import Decimal

from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from ... import texts as t
from ...config import is_admin
from ...db import async_session
from ...keyboards import (
    admin_menu_keyboard,
    cancel_keyboard,
    customer_manage_keyboard,
    customer_service_actions_keyboard,
    customer_services_keyboard,
    format_plans_list,
    main_menu,
    plans_list_keyboard,
)
from ...models import User, WalletAuditLog
from ...orders_repo import count_user_orders
from ...panel_client import PanelAPIError, panel_client
from ...plans_repo import get_plan, list_active_plans
from ...services_repo import count_user_services, create_service, list_user_services, update_service, get_service
from ...states import AdminCustomerLookup
from ...users_repo import find_user
from .base import AdminOnlyMiddleware

router = Router(name="admin_customers")
router.message.middleware(AdminOnlyMiddleware())
router.callback_query.middleware(AdminOnlyMiddleware())
logger = logging.getLogger(__name__)


def _deep_link(telegram_id: int, username: str | None) -> str:
    if username:
        return f"https://t.me/{username}"
    return f"tg://user?id={telegram_id}"


@router.message(F.text == t.ADMIN_MENU_CUSTOMERS)
async def start_lookup(message: Message, state: FSMContext):
    await state.set_state(AdminCustomerLookup.query)
    await message.answer(t.ASK_CUSTOMER_QUERY, reply_markup=cancel_keyboard())


@router.message(AdminCustomerLookup.query)
async def do_lookup(message: Message, state: FSMContext):
    user = await find_user(message.text.strip())
    if not user:
        await message.answer(t.CUSTOMER_NOT_FOUND, reply_markup=admin_menu_keyboard())
        await state.clear()
        return

    total_services, _ = await count_user_services(user.telegram_id)
    order_count = await count_user_orders(user.telegram_id)

    await state.update_data(cust_id=user.telegram_id)
    await state.set_state(AdminCustomerLookup.manage)
    await message.answer(
        t.CUSTOMER_PROFILE.format(
            telegram_id=user.telegram_id,
            username=user.username or "-",
            wallet_balance=int(user.wallet_balance),
            service_count=total_services,
            order_count=order_count,
            deep_link=_deep_link(user.telegram_id, user.username),
        ),
        reply_markup=customer_manage_keyboard(user.telegram_id),
    )


@router.callback_query(F.data == "cust_back")
async def back_to_admin(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer(t.ADMIN_MENU, reply_markup=admin_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("cust_svc_list:"))
async def list_customer_services(callback: CallbackQuery):
    telegram_id = int(callback.data.split(":")[1])
    services = await list_user_services(telegram_id)
    if not services:
        await callback.answer(t.CUSTOMER_NO_SERVICES, show_alert=True)
        return
    await callback.message.edit_text(
        t.CUSTOMER_SERVICES_HEADER.format(telegram_id=telegram_id),
        reply_markup=customer_services_keyboard(telegram_id, services),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cust_svc_view:"))
async def view_customer_service(callback: CallbackQuery):
    _, telegram_id, service_id = callback.data.split(":")
    telegram_id, service_id = int(telegram_id), int(service_id)
    service = await get_service(service_id)
    if not service or service.owner_telegram_id != telegram_id:
        await callback.answer(t.SERVICE_NOT_FOUND, show_alert=True)
        return

    remaining_days = "نامحدود"
    if service.expires_at:
        now = datetime.now(timezone.utc)
        expires = service.expires_at if service.expires_at.tzinfo else service.expires_at.replace(tzinfo=timezone.utc)
        delta = expires - now
        remaining_days = "منقضی شده" if delta.days <= 0 else f"{delta.days} روز"

    remaining_traffic = f"{service.traffic_gb} گیگ"
    try:
        panel_user = await panel_client.get_user(service.panel_username)
        bytes_used = panel_user.raw.get("usage") or panel_user.raw.get("data_usage") or panel_user.raw.get("used_traffic")
        if bytes_used:
            used_gb = bytes_used / (1024 ** 3)
            remaining = max(0, service.traffic_gb - used_gb)
            remaining_traffic = f"{remaining:.1f} از {service.traffic_gb} گیگ"
    except PanelAPIError:
        pass

    text = t.CUSTOMER_SERVICE_DETAIL.format(
        id=service.id,
        panel_username=service.panel_username,
        months=service.months,
        traffic_gb=service.traffic_gb,
        status=service.status,
        remaining_days=remaining_days,
        remaining_traffic=remaining_traffic,
        created_at=service.created_at.strftime("%Y-%m-%d") if service.created_at else "-",
        expires_at=service.expires_at.strftime("%Y-%m-%d") if service.expires_at else "نامحدود",
        link=service.subscription_link or "—",
    )
    await callback.message.edit_text(text, reply_markup=customer_service_actions_keyboard(telegram_id, service_id))
    await callback.answer()


@router.callback_query(F.data.startswith("cust_svc_disable:"))
async def disable_customer_service(callback: CallbackQuery):
    _, telegram_id, service_id = callback.data.split(":")
    telegram_id, service_id = int(telegram_id), int(service_id)
    service = await get_service(service_id)
    if not service or service.owner_telegram_id != telegram_id:
        await callback.answer(t.SERVICE_NOT_FOUND, show_alert=True)
        return
    try:
        await panel_client.disable_user(service.panel_username)
    except PanelAPIError as exc:
        logger.exception("Failed to disable panel user %s", service.panel_username)
        await callback.answer(f"خطا در پنل: {exc}", show_alert=True)
        return
    await update_service(service_id, status="disabled")
    await callback.answer(t.CUSTOMER_SERVICE_DISABLED.format(id=service_id), show_alert=True)
    services = await list_user_services(telegram_id)
    await callback.message.edit_text(
        t.CUSTOMER_SERVICES_HEADER.format(telegram_id=telegram_id),
        reply_markup=customer_services_keyboard(telegram_id, services),
    )


@router.callback_query(F.data.startswith("cust_svc_delete:"))
async def delete_customer_service(callback: CallbackQuery):
    _, telegram_id, service_id = callback.data.split(":")
    telegram_id, service_id = int(telegram_id), int(service_id)
    service = await get_service(service_id)
    if not service or service.owner_telegram_id != telegram_id:
        await callback.answer(t.SERVICE_NOT_FOUND, show_alert=True)
        return
    try:
        await panel_client.delete_user(service.panel_username)
    except PanelAPIError as exc:
        logger.exception("Failed to delete panel user %s", service.panel_username)
        await callback.answer(f"خطا در پنل: {exc}", show_alert=True)
        return
    await update_service(service_id, status="deleted")
    await callback.answer(t.CUSTOMER_SERVICE_DELETED.format(id=service_id), show_alert=True)
    services = await list_user_services(telegram_id)
    if services:
        await callback.message.edit_text(
            t.CUSTOMER_SERVICES_HEADER.format(telegram_id=telegram_id),
            reply_markup=customer_services_keyboard(telegram_id, services),
        )
    else:
        await callback.message.edit_text(t.CUSTOMER_NO_SERVICES)


@router.callback_query(F.data.startswith("cust_svc_add:"))
async def add_service_start(callback: CallbackQuery, state: FSMContext):
    telegram_id = int(callback.data.split(":")[1])
    plans = await list_active_plans()
    if not plans:
        await callback.answer(t.NO_PLANS_AVAILABLE, show_alert=True)
        return
    await state.update_data(cust_id=telegram_id)
    await state.set_state(AdminCustomerLookup.add_service_plan)
    await callback.message.edit_text(format_plans_list(plans), reply_markup=plans_list_keyboard(plans))
    await callback.answer()


@router.callback_query(AdminCustomerLookup.add_service_plan, F.data.startswith("plan_select:"))
async def add_service_confirm(callback: CallbackQuery, state: FSMContext):
    _, _, plan_id = callback.data.split(":")
    plan = await get_plan(int(plan_id))
    if not plan:
        await callback.answer(t.PLAN_NOT_FOUND, show_alert=True)
        return
    data = await state.get_data()
    telegram_id = data["cust_id"]

    panel_username = f"tg{telegram_id}_{uuid.uuid4().hex[:6]}"
    data_limit_bytes = int(plan.traffic_gb * 1024**3)
    duration_seconds = plan.months * 30 * 86400

    try:
        panel_user = await panel_client.create_active_user(
            username=panel_username,
            data_limit_bytes=data_limit_bytes,
            duration_seconds=duration_seconds,
        )
    except PanelAPIError as exc:
        logger.exception("Failed to create panel user for customer %s", telegram_id)
        await callback.answer(f"خطا در پنل: {exc}", show_alert=True)
        return

    from datetime import datetime, timedelta, timezone

    expires_at = datetime.now(timezone.utc) + timedelta(seconds=duration_seconds)
    await create_service(
        owner_telegram_id=telegram_id,
        panel_username=panel_user.username,
        panel_uuid=panel_user.uuid,
        subscription_link=panel_user.subscription_link,
        status="active",
        user_count=plan.user_count,
        months=plan.months,
        traffic_gb=plan.traffic_gb,
        price=0,
        expires_at=expires_at,
    )

    await state.clear()
    if panel_user.subscription_link:
        from ...qr_gen import generate_qr_image
        text = t.CUSTOMER_SERVICE_ADDED.format(link=panel_user.subscription_link)
        qr_photo = generate_qr_image(panel_user.subscription_link)
        await callback.message.answer_photo(qr_photo, caption=text)
    else:
        await callback.message.edit_text(
            t.CUSTOMER_SERVICE_ADDED.format(link="—")
        )
    await callback.answer()


@router.callback_query(F.data.startswith("cust_wallet:"))
async def adjust_wallet_start(callback: CallbackQuery, state: FSMContext):
    telegram_id = int(callback.data.split(":")[1])
    await state.update_data(cust_id=telegram_id)
    await state.set_state(AdminCustomerLookup.adjust_wallet_amount)
    await callback.message.edit_text(t.ASK_WALLET_ADJUST_AMOUNT)
    await callback.answer()


@router.message(AdminCustomerLookup.adjust_wallet_amount)
async def adjust_wallet_apply(message: Message, state: FSMContext):
    try:
        amount = int(message.text.strip())
    except ValueError:
        await message.answer(t.INVALID_NUMBER)
        return

    data = await state.get_data()
    telegram_id = data["cust_id"]

    async with async_session() as session:
        user = await session.get(User, telegram_id)
        if not user:
            await message.answer(t.CUSTOMER_NOT_FOUND, reply_markup=admin_menu_keyboard())
            await state.clear()
            return
        old_balance = int(user.wallet_balance)
        new_balance = old_balance + amount
        if new_balance < 0:
            new_balance = 0
        user.wallet_balance = Decimal(new_balance)
        session.add(
            WalletAuditLog(
                telegram_id=telegram_id,
                old_balance=Decimal(old_balance),
                new_balance=Decimal(new_balance),
                reason="admin adjust wallet",
            )
        )
        await session.commit()

    await state.clear()
    await message.answer(
        t.CUSTOMER_WALLET_ADJUSTED.format(old=old_balance, new=new_balance),
        reply_markup=admin_menu_keyboard(),
    )


@router.callback_query(F.data.startswith("cust_back_to:"))
async def back_to_manage(callback: CallbackQuery, state: FSMContext):
    telegram_id = int(callback.data.split(":")[1])
    user = await find_user(str(telegram_id))
    if not user:
        await callback.answer(t.CUSTOMER_NOT_FOUND, show_alert=True)
        return
    total_services, _ = await count_user_services(user.telegram_id)
    order_count = await count_user_orders(user.telegram_id)
    await state.update_data(cust_id=user.telegram_id)
    await state.set_state(AdminCustomerLookup.manage)
    await callback.message.edit_text(
        t.CUSTOMER_PROFILE.format(
            telegram_id=user.telegram_id,
            username=user.username or "-",
            wallet_balance=int(user.wallet_balance),
            service_count=total_services,
            order_count=order_count,
            deep_link=_deep_link(user.telegram_id, user.username),
        ),
        reply_markup=customer_manage_keyboard(user.telegram_id),
    )
    await callback.answer()
