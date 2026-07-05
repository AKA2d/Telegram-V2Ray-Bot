import logging
import time
import uuid

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from .. import texts as t
from ..cards_repo import get_active_card, get_next_card
from ..config import ADMIN_TELEGRAM_ID
from ..keyboards import cancel_keyboard, confirm_keyboard, main_menu, order_review_keyboard, payment_keyboard
from ..orders_repo import create_order, update_order
from ..panel_client import PanelAPIError, panel_client
from ..services_repo import create_service
from ..settings_repo import calculate_price
from ..states import BuyService
from datetime import datetime, timezone

router = Router(name="buy_service")
logger = logging.getLogger("buy_service")


def _deep_link(user) -> str:
    if user.username:
        return f"https://t.me/{user.username}"
    return f"tg://user?id={user.id}"


def _parse_positive_int(text: str) -> int | None:
    try:
        value = int(text.strip())
        return value if value > 0 else None
    except ValueError:
        return None


@router.message(F.text == t.MAIN_MENU_BUY)
async def start_buy(message: Message, state: FSMContext):
    await state.set_state(BuyService.user_count)
    await message.answer(t.ASK_USER_COUNT, reply_markup=cancel_keyboard())


@router.message(BuyService.user_count)
async def set_user_count(message: Message, state: FSMContext):
    value = _parse_positive_int(message.text)
    if value is None:
        await message.answer(t.INVALID_NUMBER)
        return
    await state.update_data(user_count=value)
    await state.set_state(BuyService.months)
    await message.answer(t.ASK_MONTHS, reply_markup=cancel_keyboard())


@router.message(BuyService.months)
async def set_months(message: Message, state: FSMContext):
    value = _parse_positive_int(message.text)
    if value is None:
        await message.answer(t.INVALID_NUMBER)
        return
    await state.update_data(months=value)
    await state.set_state(BuyService.traffic_gb)
    await message.answer(t.ASK_TRAFFIC, reply_markup=cancel_keyboard())


@router.message(BuyService.traffic_gb)
async def set_traffic(message: Message, state: FSMContext):
    value = _parse_positive_int(message.text)
    if value is None:
        await message.answer(t.INVALID_NUMBER)
        return
    await state.update_data(traffic_gb=value)
    data = await state.get_data()
    price = await calculate_price(data["user_count"], data["months"], value)
    await state.update_data(price=int(price))
    await state.set_state(BuyService.confirm)
    await message.answer(
        t.ORDER_SUMMARY.format(
            user_count=data["user_count"], months=data["months"], traffic_gb=value, price=int(price)
        ),
        reply_markup=confirm_keyboard(),
    )


@router.message(BuyService.confirm, F.text == t.BTN_CANCEL)
async def cancel_confirm(message: Message, state: FSMContext):
    await state.clear()
    is_admin = message.from_user.id == ADMIN_TELEGRAM_ID
    await message.answer(t.CANCELLED, reply_markup=main_menu(is_admin))


@router.message(BuyService.confirm, F.text == t.BTN_CONFIRM)
async def confirm_order(message: Message, state: FSMContext):
    data = await state.get_data()
    telegram_id = message.from_user.id
    panel_username = f"tg{telegram_id}_{uuid.uuid4().hex[:6]}"
    data_limit_bytes = data["traffic_gb"] * 1024**3
    duration_seconds = data["months"] * 30 * 86400
    expire_at = int(time.time()) + duration_seconds

    try:
        panel_user = await panel_client.create_user(
            username=panel_username,
            data_limit_bytes=data_limit_bytes,
            duration_seconds=duration_seconds,
        )
    except PanelAPIError as exc:
        logger.exception("Panel error while creating user")
        await message.bot.send_message(ADMIN_TELEGRAM_ID, t.PANEL_ERROR_ADMIN.format(error=str(exc)))
        await message.answer(t.ERROR_GENERIC, reply_markup=main_menu(message.from_user.id == ADMIN_TELEGRAM_ID))
        await state.clear()
        return

    service = await create_service(
        owner_telegram_id=telegram_id,
        panel_username=panel_user.username,
        panel_uuid=panel_user.uuid,
        subscription_link=panel_user.subscription_link,
        status="pending_payment",
        user_count=data["user_count"],
        months=data["months"],
        traffic_gb=data["traffic_gb"],
        price=data["price"],
        expires_at=datetime.fromtimestamp(expire_at, tz=timezone.utc),
    )

    order = await create_order(
        telegram_id=telegram_id,
        service_id=service.id,
        type="new_service",
        amount=data["price"],
        status="awaiting_receipt",
    )

    await message.answer(t.ORDER_CREATED.format(link=panel_user.subscription_link or "—"))

    card = await get_active_card()
    if not card:
        await message.answer(t.NO_ACTIVE_CARD, reply_markup=main_menu(message.from_user.id == ADMIN_TELEGRAM_ID))
        await state.clear()
        return

    await state.update_data(order_id=order.id, current_card_id=card.id)
    await state.set_state(BuyService.awaiting_receipt)
    await message.answer(
        t.PAYMENT_INSTRUCTIONS.format(amount=data["price"], card_number=card.card_number, holder_name=card.holder_name or ""),
        reply_markup=payment_keyboard(),
    )


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
    from datetime import datetime as dt

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
        submitted_at=dt.now(timezone.utc),
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
