from datetime import datetime, timedelta, timezone
import time

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from ... import texts as t
from ...orders_repo import get_order, list_pending_orders, transition_order_status, update_order
from ...panel_client import PanelAPIError, panel_client
from ...xenet_client import XenetAPIError, xenet_client
from ...services_repo import get_service, update_service
from ...settings_repo import get_setting, set_setting
from ...users_repo import get_or_create_user
from .base import AdminOnlyMiddleware

router = Router(name="admin_orders")
router.message.middleware(AdminOnlyMiddleware())
router.callback_query.middleware(AdminOnlyMiddleware())


@router.message(F.text == t.ADMIN_MENU_ORDERS)
async def list_orders(message: Message):
    orders = await list_pending_orders()
    if not orders:
        await message.answer(t.NO_PENDING_ORDERS)
        return
    for order in orders:
        user_display = f"شناسه {order.telegram_id}"
        text = (
            f"سفارش #{order.id} — {order.type}\n"
            f"کاربر: {user_display}\n"
            f"مبلغ: {int(order.amount):,} تومان\n"
            f"رسید: {order.receipt_text or '(عکس)'}"
        )
        from ...keyboards import order_review_keyboard

        if order.receipt_photo_file_id:
            try:
                await message.answer_photo(order.receipt_photo_file_id, caption=text, reply_markup=order_review_keyboard(order.id))
            except Exception:
                await message.answer(text, reply_markup=order_review_keyboard(order.id))
        else:
            await message.answer(text, reply_markup=order_review_keyboard(order.id))


@router.callback_query(F.data.startswith("order_approve:"))
async def approve_order(callback: CallbackQuery):
    order_id = int(callback.data.split(":")[1])
    order = await get_order(order_id)
    if not order:
        await callback.answer(t.ORDER_ALREADY_PROCESSED, show_alert=True)
        return
    if order.status != "awaiting_admin_review":
        await callback.answer(t.ORDER_ALREADY_PROCESSED, show_alert=True)
        return

    if order.type == "new_service" and order.service_id:
        # Claim the order before the slow external call. A second callback can
        # no longer create another panel account while this one is in flight.
        if not await transition_order_status(order_id, "awaiting_admin_review", "provisioning"):
            await callback.answer(t.ORDER_ALREADY_PROCESSED, show_alert=True)
            return

        service = await get_service(order.service_id)
        if not service:
            await transition_order_status(order_id, "provisioning", "awaiting_admin_review")
            await callback.message.answer(t.PANEL_ERROR_ADMIN.format(error="Service record was not found."))
            await callback.answer()
            return

        try:
            if service.service_type == "unlimited":
                # Unlimited service - use Xenet API
                idempotency_key = f"admin_order_{order.id}_{int(time.time())}"
                xenet_config = await xenet_client.create_v2_account(
                    users=service.user_count,
                    idempotency_key=idempotency_key,
                )
                subscription_link = xenet_config.sub_link
                xenet_account_id = xenet_config.id
                duration_seconds = service.months * 30 * 86400
            else:
                # Traffic-based service - use Panel API
                duration_seconds = service.months * 30 * 86400
                data_limit_bytes = int(service.traffic_gb * 1024**3)
                # A prior request can succeed at the panel while its response is
                # lost. On retry, reuse that account rather than creating another.
                try:
                    panel_user = await panel_client.get_user(service.panel_username)
                except PanelAPIError as lookup_error:
                    if lookup_error.status_code != 404:
                        raise
                    panel_user = await panel_client.create_active_user(
                        username=service.panel_username,
                        data_limit_bytes=data_limit_bytes,
                        duration_seconds=duration_seconds,
                    )
                subscription_link = panel_user.subscription_link
                xenet_account_id = None
        except Exception as exc:
            # Leave the receipt reviewable and the existing buttons usable.
            # The admin can correct the panel issue and approve again.
            await transition_order_status(order_id, "provisioning", "awaiting_admin_review")
            await callback.message.answer(t.PANEL_ERROR_ADMIN.format(error=str(exc)))
            await callback.answer()
            return

        expires_at = datetime.now(timezone.utc) + timedelta(seconds=service.months * 30 * 86400)
        update_fields = {
            "status": "active",
            "subscription_link": subscription_link,
            "expires_at": expires_at,
            "xenet_account_id": xenet_account_id,
        }
        # For unlimited services, use the name from Xenet API as panel_username
        if service.service_type == "unlimited":
            update_fields["panel_username"] = xenet_config.name
        await update_service(service.id, **update_fields)
        await update_order(order_id, status="approved", reviewed_at=datetime.now(timezone.utc))
        current_sold = int(await get_setting("sold_amount"))
        await set_setting("sold_amount", str(current_sold + int(order.amount)))
        current_traffic = int(float(await get_setting("sold_traffic")))
        await set_setting("sold_traffic", str(current_traffic + float(service.traffic_gb if service.service_type == "traffic_based" else 0)))
        await callback.bot.send_message(order.telegram_id, t.ORDER_APPROVED_CUSTOMER)
        traffic_text = "نامحدود" if service.service_type == "unlimited" else f"{service.traffic_gb} گیگابایت"
        user_count_text = "نامحدود" if service.service_type == "traffic_based" else service.user_count
        from ...qr_gen import generate_qr_image
        from ...plans_repo import find_plan_for_service
        plan = await find_plan_for_service(service)
        plan_name = plan.name if plan else service.panel_username
        text = t.SERVICE_ACTIVATED_DETAILED.format(
            username=update_fields.get("panel_username", service.panel_username),
            plan_name=plan_name,
            price=f"{int(order.amount):,}",
            months=service.months * 30,
            user_count=user_count_text,
            traffic=traffic_text,
            link=subscription_link or "—",
        )
        if subscription_link:
            qr_photo = generate_qr_image(subscription_link)
            await callback.bot.send_photo(order.telegram_id, qr_photo, caption=text)
        else:
            await callback.bot.send_message(order.telegram_id, text)
        await callback.bot.send_message(order.telegram_id, t.POST_PURCHASE_HINT)
    else:
        # Non-provisioning orders have no external account creation step, but
        # still use an atomic status claim to reject duplicate button taps.
        if not await transition_order_status(order_id, "awaiting_admin_review", "approved"):
            await callback.answer(t.ORDER_ALREADY_PROCESSED, show_alert=True)
            return
        await update_order(order_id, reviewed_at=datetime.now(timezone.utc))
        current_sold = int(await get_setting("sold_amount"))
        await set_setting("sold_amount", str(current_sold + int(order.amount)))

    if order.type == "wallet_topup":
        from ...db import async_session
        from ...models import User, WalletAuditLog

        async with async_session() as session:
            user = await session.get(User, order.telegram_id)
            old_balance = user.wallet_balance
            user.wallet_balance = old_balance + order.amount
            session.add(
                WalletAuditLog(
                    telegram_id=order.telegram_id,
                    old_balance=old_balance,
                    new_balance=user.wallet_balance,
                    reason=f"wallet_topup order #{order.id}",
                )
            )
            await session.commit()
            new_balance = user.wallet_balance
        await callback.bot.send_message(order.telegram_id, t.WALLET_TOPUP_APPROVED_CUSTOMER.format(balance=int(new_balance)))

    elif order.type == "extend_service" and order.service_id:
        import json
        from ..manage_service import _apply_extend
        extend_details_str = await get_setting(f"extend_order_{order.id}")
        extend_details = json.loads(extend_details_str) if extend_details_str else {}
        service = await get_service(order.service_id)
        if service:
            await _apply_extend(
                service,
                extend_details.get("add_months", 0),
                extend_details.get("add_traffic", 0),
            )
            await callback.bot.send_message(order.telegram_id, t.EXTEND_SUCCESS)

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer("تایید شد")


@router.callback_query(F.data.startswith("order_reject:"))
async def reject_order(callback: CallbackQuery):
    order_id = int(callback.data.split(":")[1])
    order = await get_order(order_id)
    if not order or order.status != "awaiting_admin_review":
        await callback.answer(t.ORDER_ALREADY_PROCESSED, show_alert=True)
        return

    await update_order(order_id, status="rejected", reviewed_at=datetime.now(timezone.utc))

    if order.type == "new_service" and order.service_id:
        service = await get_service(order.service_id)
        if service.status == "pending_payment":
            # Account was never created (only happens on approval), so
            # there's nothing to disable/delete on the provider side.
            await update_service(service.id, status="rejected")
        else:
            await update_service(service.id, status="disabled")
            try:
                if service.service_type == "unlimited" and service.xenet_account_id:
                    # For unlimited services, try to refund/delete on Xenet
                    await xenet_client.refund_v2_account(service.xenet_account_id)
                else:
                    # For traffic-based services, disable on Panel
                    await panel_client.disable_user(service.panel_uuid or service.panel_username)
            except (PanelAPIError, XenetAPIError):
                pass

    await callback.bot.send_message(order.telegram_id, t.ORDER_REJECTED_CUSTOMER)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer("رد شد")
