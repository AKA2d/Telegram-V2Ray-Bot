from datetime import datetime, timedelta, timezone

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import CallbackQuery, Message

from .. import texts as t
from ..config import is_admin
from ..keyboards import (
    extend_confirm_keyboard,
    extend_final_keyboard,
    format_plans_list,
    payment_keyboard,
    plans_list_keyboard,
    service_actions_keyboard,
    services_list_keyboard,
)
from ..panel_client import PanelAPIError, panel_client
from ..plans_repo import get_plan, list_active_plans
from ..services_repo import find_service_by_link_or_uuid, get_service, list_user_services, update_service
from ..states import BuyService, ExtendService

router = Router(name="manage_service")


def _can_manage(service, user_id: int) -> bool:
    """Check if user can manage this service (owner or admin)."""
    return service.owner_telegram_id == user_id or is_admin(user_id)


def _format_remaining_days(expires_at) -> str:
    if not expires_at:
        return "نامحدود"
    now = datetime.now(timezone.utc)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    delta = expires_at - now
    days = delta.days
    if days <= 0:
        return "منقضی شده"
    return f"{days} روز"


def _format_traffic(bytes_used: int | None, total_gb: int) -> str:
    if bytes_used is None:
        return f"{total_gb} گیگ (نامشخص)"
    used_gb = bytes_used / (1024 ** 3)
    remaining = total_gb - used_gb
    if remaining < 0:
        remaining = 0
    return f"{remaining:.1f} از {total_gb} گیگ"


async def _format_service(service) -> str:
    remaining_days = _format_remaining_days(service.expires_at)

    remaining_traffic = f"{service.traffic_gb} گیگ"
    if service.status == "active":
        try:
            panel_user = await panel_client.get_user(service.panel_username)
            bytes_used = panel_user.raw.get("usage") or panel_user.raw.get("data_usage") or panel_user.raw.get("used_traffic")
            if bytes_used:
                remaining_traffic = _format_traffic(bytes_used, service.traffic_gb)
        except PanelAPIError:
            pass

    link = service.subscription_link or "—"
    if service.status != "active":
        link = "غیرفعال"

    return t.SERVICE_DETAIL.format(
        id=service.id,
        panel_username=service.panel_username,
        months=service.months,
        traffic_gb=service.traffic_gb,
        status=service.status,
        remaining_days=remaining_days,
        remaining_traffic=remaining_traffic,
        created_at=service.created_at.strftime("%Y-%m-%d") if service.created_at else "-",
        expires_at=service.expires_at.strftime("%Y-%m-%d") if service.expires_at else "نامحدود",
        link=link,
    )


@router.message(F.text == t.MAIN_MENU_MANAGE)
async def manage_menu(message: Message):
    services = await list_user_services(message.from_user.id)
    if not services:
        await message.answer(t.NO_SERVICES)
        return
    await message.answer(t.MANAGE_SERVICE_PROMPT, reply_markup=services_list_keyboard(services))


@router.callback_query(F.data.startswith("svc_view:"))
async def view_service(callback: CallbackQuery):
    service_id = int(callback.data.split(":")[1])
    service = await get_service(service_id)
    if not service or not _can_manage(service, callback.from_user.id):
        await callback.answer(t.SERVICE_NOT_FOUND, show_alert=True)
        return
    await callback.message.answer(await _format_service(service), reply_markup=service_actions_keyboard(service.id, service.status, is_admin(callback.from_user.id)))
    await callback.answer()


@router.callback_query(F.data.startswith("svc_regen:"))
async def regenerate_service(callback: CallbackQuery):
    service_id = int(callback.data.split(":")[1])
    service = await get_service(service_id)
    if not service or not _can_manage(service, callback.from_user.id):
        await callback.answer(t.SERVICE_NOT_FOUND, show_alert=True)
        return
    if service.status != "active":
        await callback.answer("سرویس فعال نیست.", show_alert=True)
        return
    try:
        panel_user = await panel_client.regenerate_subscription(service.panel_uuid or service.panel_username)
    except PanelAPIError:
        await callback.answer(t.ERROR_GENERIC, show_alert=True)
        return
    await update_service(service.id, subscription_link=panel_user.subscription_link, panel_uuid=panel_user.uuid or service.panel_uuid)
    if panel_user.subscription_link:
        from ..qr_gen import generate_qr_image
        text = t.REGENERATE_DONE.format(link=panel_user.subscription_link)
        qr_photo = generate_qr_image(panel_user.subscription_link)
        await callback.message.answer_photo(qr_photo, caption=text)
    else:
        await callback.message.answer(t.REGENERATE_DONE.format(link="—"))
    await callback.answer()


@router.callback_query(F.data.startswith("svc_qr:"))
async def get_qr_code(callback: CallbackQuery):
    service_id = int(callback.data.split(":")[1])
    service = await get_service(service_id)
    if not service or not _can_manage(service, callback.from_user.id):
        await callback.answer(t.SERVICE_NOT_FOUND, show_alert=True)
        return
    if not service.subscription_link:
        await callback.answer("لینک اشتراک وجود ندارد.", show_alert=True)
        return
    if service.status != "active":
        await callback.answer("سرویس فعال نیست.", show_alert=True)
        return
    from ..qr_gen import generate_qr_image
    qr_photo = generate_qr_image(service.subscription_link)
    await callback.message.answer_photo(qr_photo, caption="📱 QR Code لینک اشتراک")
    await callback.answer()


@router.callback_query(F.data.startswith("svc_disable:"))
async def disable_service(callback: CallbackQuery):
    service_id = int(callback.data.split(":")[1])
    service = await get_service(service_id)
    if not service or not _can_manage(service, callback.from_user.id):
        await callback.answer(t.SERVICE_NOT_FOUND, show_alert=True)
        return
    if service.status != "active":
        await callback.answer("سرویس در حال حاضر فعال نیست.", show_alert=True)
        return
    try:
        await panel_client.disable_user(service.panel_username)
    except PanelAPIError:
        await callback.answer(t.ERROR_GENERIC, show_alert=True)
        return
    await update_service(service_id, status="disabled")
    await callback.message.edit_text("سرویس با موفقیت غیرفعال شد.")
    await callback.answer()


@router.callback_query(F.data.startswith("svc_enable:"))
async def enable_service(callback: CallbackQuery):
    service_id = int(callback.data.split(":")[1])
    service = await get_service(service_id)
    if not service or not _can_manage(service, callback.from_user.id):
        await callback.answer(t.SERVICE_NOT_FOUND, show_alert=True)
        return
    if service.status == "active":
        await callback.answer("سرویس در حال حاضر فعال است.", show_alert=True)
        return
    try:
        await panel_client.enable_user(service.panel_username)
    except PanelAPIError:
        await callback.answer(t.ERROR_GENERIC, show_alert=True)
        return
    await update_service(service_id, status="active")
    await callback.message.edit_text("سرویس با موفقیت فعال شد.")
    await callback.answer()


@router.callback_query(F.data.startswith("svc_delete:"))
async def delete_service(callback: CallbackQuery):
    service_id = int(callback.data.split(":")[1])
    service = await get_service(service_id)
    if not service or not _can_manage(service, callback.from_user.id):
        await callback.answer(t.SERVICE_NOT_FOUND, show_alert=True)
        return
    try:
        await panel_client.delete_user(service.panel_username)
    except PanelAPIError:
        await callback.answer(t.ERROR_GENERIC, show_alert=True)
        return
    await update_service(service_id, status="deleted")
    await callback.message.edit_text("سرویس با موفقیت از پنل حذف شد.")
    await callback.answer()


@router.callback_query(F.data.startswith("svc_increase:"))
async def increase_users(callback: CallbackQuery):
    await callback.answer(t.PHASE2_NOT_AVAILABLE, show_alert=True)


@router.callback_query(F.data.startswith("svc_extend:"))
async def extend_start(callback: CallbackQuery, state: FSMContext):
    service_id = int(callback.data.split(":")[1])
    service = await get_service(service_id)
    if not service or not _can_manage(service, callback.from_user.id):
        await callback.answer(t.SERVICE_NOT_FOUND, show_alert=True)
        return
    if service.status != "active":
        await callback.answer("سرویس فعال نیست.", show_alert=True)
        return

    remaining_days = f"{_format_remaining_days(service.expires_at)} روز"
    remaining_traffic = f"{service.traffic_gb} گیگ"
    if service.status == "active":
        try:
            panel_user = await panel_client.get_user(service.panel_username)
            bytes_used = panel_user.raw.get("usage") or panel_user.raw.get("data_usage") or panel_user.raw.get("used_traffic")
            if bytes_used:
                remaining_traffic = _format_traffic(bytes_used, service.traffic_gb)
        except PanelAPIError:
            pass

    await state.update_data(service_id=service_id)
    await state.set_state(ExtendService.confirm)
    await callback.message.edit_text(
        t.EXTEND_CONFIRM.format(
            id=service.id,
            remaining_days=remaining_days,
            remaining_traffic=remaining_traffic,
        ),
        reply_markup=extend_confirm_keyboard(service_id),
    )
    await callback.answer()


@router.callback_query(ExtendService.confirm, F.data.startswith("extend_confirm:yes:"))
async def extend_choose_plan(callback: CallbackQuery, state: FSMContext):
    plans = await list_active_plans()
    if not plans:
        await callback.answer(t.NO_PLANS_AVAILABLE, show_alert=True)
        await state.clear()
        return
    await state.set_state(ExtendService.choosing_plan)
    await callback.message.edit_text(
        format_plans_list(plans),
        reply_markup=plans_list_keyboard(plans),
    )
    await callback.answer()


@router.callback_query(ExtendService.confirm, F.data == "plan_cancel")
async def extend_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(t.EXTEND_CANCELLED)
    await callback.answer()


@router.callback_query(ExtendService.choosing_plan, F.data.startswith("plan_select:"))
async def extend_select_plan(callback: CallbackQuery, state: FSMContext):
    _, _, plan_id = callback.data.split(":")
    plan = await get_plan(int(plan_id))
    if not plan:
        await callback.answer(t.PLAN_NOT_FOUND, show_alert=True)
        return

    data = await state.get_data()
    service_id = data["service_id"]
    service = await get_service(service_id)

    await state.update_data(
        plan_id=plan.id,
        plan_name=plan.name,
        months=plan.months,
        traffic_gb=plan.traffic_gb,
        price=int(plan.price),
    )
    await state.set_state(ExtendService.confirm_plan)
    await callback.message.edit_text(
        t.EXTEND_PLAN_SUMMARY.format(
            id=service.id,
            plan_name=plan.name,
            months=plan.months,
            traffic_gb=plan.traffic_gb,
            price=int(plan.price),
        ),
        reply_markup=extend_final_keyboard(plan.id),
    )
    await callback.answer()


@router.callback_query(ExtendService.confirm_plan, F.data.startswith("extend_final:no:"))
async def extend_plan_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(t.EXTEND_CANCELLED)
    await callback.answer()


@router.callback_query(ExtendService.confirm_plan, F.data.startswith("extend_final:yes:"))
async def extend_apply(callback: CallbackQuery, state: FSMContext):
    import json
    data = await state.get_data()
    service_id = data["service_id"]
    add_months = data["months"]
    add_traffic = data["traffic_gb"]
    price = data["price"]

    service = await get_service(service_id)
    if not service or not _can_manage(service, callback.from_user.id):
        await callback.answer(t.SERVICE_NOT_FOUND, show_alert=True)
        await state.clear()
        return

    # Check wallet balance
    from ..db import async_session
    from ..models import User, WalletAuditLog

    async with async_session() as session:
        user = await session.get(User, callback.from_user.id)
        balance = user.wallet_balance if user else 0

    if balance >= price:
        # Pay with wallet
        async with async_session() as session:
            user = await session.get(User, callback.from_user.id)
            old_balance = user.wallet_balance
            user.wallet_balance = old_balance - price
            session.add(
                WalletAuditLog(
                    telegram_id=callback.from_user.id,
                    old_balance=old_balance,
                    new_balance=user.wallet_balance,
                    reason=f"extend service #{service_id}",
                )
            )
            await session.commit()

        # Apply extend
        await _apply_extend(service, add_months, add_traffic)
        await state.clear()
        await callback.message.edit_text(t.EXTEND_SUCCESS)
        await callback.message.answer(t.POST_PURCHASE_HINT)
        await callback.answer()
    else:
        # Not enough balance: show card for payment
        from ..cards_repo import get_round_robin_card
        from ..orders_repo import create_order
        from ..keyboards import payment_keyboard

        extend_details = json.dumps({
            "service_id": service_id,
            "add_months": add_months,
            "add_traffic": add_traffic,
        })

        from ..settings_repo import set_setting
        order = await create_order(
            telegram_id=callback.from_user.id,
            service_id=service_id,
            type="extend_service",
            amount=price,
            status="awaiting_receipt",
        )
        await set_setting(f"extend_order_{order.id}", extend_details)

        card = await get_round_robin_card()
        if not card:
            await callback.answer(t.NO_ACTIVE_CARD, show_alert=True)
            await state.clear()
            return

        await state.update_data(order_id=order.id, current_card_id=card.id, price=price)
        await state.set_state(BuyService.awaiting_receipt)
        await callback.message.answer(
            t.PAYMENT_INSTRUCTIONS.format(
                amount=price, card_number=card.card_number, holder_name=card.holder_name or ""
            ),
            reply_markup=payment_keyboard(),
        )
        await callback.answer()


async def _apply_extend(service, add_months: int, add_traffic: int):
    """Apply extend to service in DB and panel."""
    from datetime import timedelta
    from ..db import async_session
    from ..services_repo import update_service

    new_traffic = service.traffic_gb + add_traffic
    now = datetime.now(timezone.utc)
    if service.expires_at:
        expires = service.expires_at if service.expires_at.tzinfo else service.expires_at.replace(tzinfo=timezone.utc)
        if expires > now:
            new_expires = expires + timedelta(days=add_months * 30)
        else:
            new_expires = now + timedelta(days=add_months * 30)
    else:
        new_expires = now + timedelta(days=add_months * 30)

    await update_service(service.id, traffic_gb=new_traffic, expires_at=new_expires, months=service.months + add_months)

    try:
        data_limit_bytes = int(new_traffic * 1024**3)
        expire_timestamp = int(new_expires.timestamp())
        await panel_client.update_user_limits(service.panel_username, data_limit_bytes, expire_timestamp)
    except PanelAPIError:
        pass


@router.message(default_state, F.text.regexp(r"^[A-Za-z0-9\-_:/.]{6,}$"))
async def lookup_by_text(message: Message):
    from ..config import is_admin
    service = await find_service_by_link_or_uuid(message.text.strip())
    if not service:
        return
    # Admin can manage any service, users can only manage their own
    if not is_admin(message.from_user.id) and service.owner_telegram_id != message.from_user.id:
        return
    await message.answer(await _format_service(service), reply_markup=service_actions_keyboard(service.id, service.status, is_admin(message.from_user.id)))
