import logging
import uuid
from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from .. import texts as t
from ..cards_repo import get_active_card, get_next_card
from ..config import ADMIN_TELEGRAM_ID
from ..keyboards import main_menu, order_review_keyboard, payment_keyboard, plans_list_keyboard
from ..orders_repo import create_order, update_order
from ..panel_client import PanelAPIError, panel_client
from ..plans_repo import get_plan, list_active_plans
from ..services_repo import create_service
from ..states import BuyService

router = Router(name="buy_service")
logger = logging.getLogger("buy_service")


def _deep_link(user) -> str:
    if user.username:
        return f"https://t.me/{user.username}"
    return f"tg://user?id={user.id}"


@router.message(F.text == t.MAIN_MENU_BUY)
async def start_buy(message: Message, state: FSMContext):
    plans = await list_active_plans()
    if not plans:
        await message.answer(t.NO_PLANS_AVAILABLE, reply_markup=main_menu(message.from_user.id == ADMIN_TELEGRAM_ID))
        return
    await state.set_state(BuyService.choosing_plan)
    await message.answer(t.CHOOSE_PLAN_PROMPT, reply_markup=plans_list_keyboard(plans))


@router.callback_query(BuyService.choosing_plan, F.data.startswith("plan_select:"))
async def confirm_order(callback: CallbackQuery, state: FSMContext):
    plan_id = int(callback.data.split(":")[1])
    plan = await get_plan(plan_id)
    if not plan or not plan.is_active:
        await callback.answer(t.PLAN_NOT_FOUND, show_alert=True)
        return

    telegram_id = callback.from_user.id
    panel_username = f"tg{telegram_id}_{uuid.uuid4().hex[:6]}"
    data_limit_bytes = plan.traffic_gb * 1024**3
    duration_seconds = plan.months * 30 * 86400

    try:
        panel_user = await panel_client.create_user(
            username=panel_username,
            data_limit_bytes=data_limit_bytes,
            duration_seconds=duration_seconds,
        )
    except PanelAPIError as exc:
        logger.exception("Panel error while creating user")
        await callback.bot.send_message(ADMIN_TELEGRAM_ID, t.PANEL_ERROR_ADMIN.format(error=str(exc)))
        await callback.message.answer(
            t.ERROR_GENERIC, reply_markup=main_menu(telegram_id == ADMIN_TELEGRAM_ID)
        )
        await state.clear()
        await callback.answer()
        return

    service = await create_service(
        owner_telegram_id=telegram_id,
        panel_username=panel_user.username,
        panel_uuid=panel_user.uuid,
        subscription_link=panel_user.subscription_link,
        status="pending_payment",
        user_count=plan.user_count,
        months=plan.months,
        traffic_gb=plan.traffic_gb,
        price=plan.price,
        expires_at=None,
    )

    order = await create_order(
        telegram_id=telegram_id,
        service_id=service.id,
        type="new_service",
        amount=plan.price,
        status="awaiting_receipt",
    )

    await callback.message.answer(t.ORDER_CREATED.format(link=panel_user.subscription_link or "—"))

    card = await get_active_card()
    if not card:
        await callback.message.answer(
            t.NO_ACTIVE_CARD, reply_markup=main_menu(telegram_id == ADMIN_TELEGRAM_ID)
        )
        await state.clear()
        await callback.answer()
        return

    await state.update_data(order_id=order.id, current_card_id=card.id, price=int(plan.price))
    await state.set_state(BuyService.awaiting_receipt)
    await callback.message.answer(
        t.PAYMENT_INSTRUCTIONS.format(
            amount=int(plan.price), card_number=card.card_number, holder_name=card.holder_name or ""
        ),
        reply_markup=payment_keyboard(),
    )
    await callback.answer()


@router.message(BuyService.awaiting_receipt, F.text == t.BTN_NEXT_CARD)
async def next_card_buy(message: Message, state: FSMContext):
    data = await state.get_data()
    card = await get_next_card(data.get("current_card_id"))
    if not card:
        await message.answer(t.NO_MORE_CARDS)
        return
    await state.update_data(current_card_id=card.id)
    await message.answer(
        t.PAYMENT_INSTRUCTIONS.format(
            amount=data["price"], card_number=card.card_number, holder_name=card.holder_name or ""
        ),
        reply_markup=payment_keyboard(),
    )


@router.message(BuyService.awaiting_receipt, F.photo)
async def receipt_photo(message: Message, state: FSMContext):
    await _handle_receipt(message, state, photo_file_id=message.photo[-1].file_id, text=message.caption)


@router.message(BuyService.awaiting_receipt, F.text)
async def receipt_text(message: Message, state: FSMContext):
    if message.text == t.BTN_NEXT_CARD:
        return
    await _handle_receipt(message, state, photo_file_id=None, text=message.text)


async def _handle_receipt(message: Message, state: FSMContext, photo_file_id: str | None, text: str | None):
    data = await state.get_data()
    order_id = data["order_id"]
    card = None
    if data.get("current_card_id"):
        from ..cards_repo import list_cards

        cards = {c.id: c for c in await list_cards()}
        card = cards.get(data["current_card_id"])

    await update_order(
        order_id,
        receipt_text=text,
        receipt_photo_file_id=photo_file_id,
        status="awaiting_admin_review",
        submitted_at=datetime.now(timezone.utc),
        card_used=card.card_number if card else None,
    )

    is_admin = message.from_user.id == ADMIN_TELEGRAM_ID
    await message.answer(t.RECEIPT_RECEIVED, reply_markup=main_menu(is_admin))
    await state.clear()

    user_display = f"@{message.from_user.username}" if message.from_user.username else message.from_user.full_name
    notice = t.NEW_ORDER_ADMIN_NOTICE.format(
        order_type="خرید سرویس جدید",
        user_display=user_display,
        telegram_id=message.from_user.id,
        deep_link=_deep_link(message.from_user),
        amount=data["price"],
        card=card.card_number if card else "-",
    )

    if photo_file_id:
        await message.bot.send_photo(
            ADMIN_TELEGRAM_ID, photo_file_id, caption=notice, reply_markup=order_review_keyboard(order_id)
        )
    else:
        await message.bot.send_message(
            ADMIN_TELEGRAM_ID, f"{notice}\n\nرسید (متن):\n{text}", reply_markup=order_review_keyboard(order_id)
        )
