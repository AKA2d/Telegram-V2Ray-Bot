from datetime import datetime, timedelta, timezone

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from ... import texts as t
from ...orders_repo import get_order, list_pending_orders, update_order
from ...panel_client import PanelAPIError, panel_client
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
            f"مبلغ: {int(order.amount)} تومان\n"
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

    await update_order(order_id, status="approved", reviewed_at=datetime.now(timezone.utc))

    # Increment sold amount for stats tracking
    current_sold = int(await get_setting("sold_amount"))
    await set_setting("sold_amount", str(current_sold + int(order.amount)))

    if order.type == "new_service" and order.service_id:
        service = await get_service(order.service_id)
        # Increment sold traffic for stats tracking
        current_traffic = int(float(await get_setting("sold_traffic")))
        await set_setting("sold_traffic", str(current_traffic + float(service.traffic_gb)))
        try:
            duration_seconds = service.months * 30 * 86400
            data_limit_bytes = int(service.traffic_gb * 1024**3)
            panel_user = await panel_client.create_active_user(
                username=service.panel_username,
                data_limit_bytes=data_limit_bytes,
                duration_seconds=duration_seconds,
            )
        except PanelAPIError as exc:
            await callback.message.answer(t.PANEL_ERROR_ADMIN.format(error=str(exc)))
            await callback.answer()
            return
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=service.months * 30 * 86400)
        await update_service(
            service.id,
            status="active",
            subscription_link=panel_user.subscription_link,
            expires_at=expires_at,
        )
        await callback.bot.send_message(order.telegram_id, t.ORDER_APPROVED_CUSTOMER)
        if panel_user.subscription_link:
            from ...qr_gen import generate_qr_image
            text = t.SERVICE_ACTIVATED_CUSTOMER.format(link=panel_user.subscription_link)
            qr_photo = generate_qr_image(panel_user.subscription_link)
            await callback.bot.send_photo(order.telegram_id, qr_photo, caption=text)
        else:
            await callback.bot.send_message(
                order.telegram_id, t.SERVICE_ACTIVATED_CUSTOMER.format(link="—")
            )
        await callback.bot.send_message(order.telegram_id, t.POST_PURCHASE_HINT)
    elif order.type == "wallet_topup":
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
            # Panel user was never created (only happens on approval), so
            # there's nothing to disable on the panel side.
            await update_service(service.id, status="rejected")
        else:
            await update_service(service.id, status="disabled")
            try:
                await panel_client.disable_user(service.panel_uuid or service.panel_username)
            except PanelAPIError:
                pass

    await callback.bot.send_message(order.telegram_id, t.ORDER_REJECTED_CUSTOMER)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer("رد شد")
