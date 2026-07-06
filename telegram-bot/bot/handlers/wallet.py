from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from .. import texts as t
from ..cards_repo import get_next_card, get_round_robin_card, list_cards
from ..config import ADMIN_TELEGRAM_ID
from ..keyboards import cancel_keyboard, main_menu, order_review_keyboard, payment_keyboard
from ..orders_repo import create_order, update_order
from ..states import TopUp

router = Router(name="wallet")


def _deep_link(user) -> str:
    if user.username:
        return f"https://t.me/{user.username}"
    return f"tg://user?id={user.id}"


@router.message(F.text == t.MAIN_MENU_TOPUP)
async def start_topup(message: Message, state: FSMContext):
    await state.set_state(TopUp.amount)
    await message.answer(t.ASK_TOPUP_AMOUNT, reply_markup=cancel_keyboard())


@router.message(TopUp.amount)
async def set_amount(message: Message, state: FSMContext):
    try:
        amount = int(message.text.strip())
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer(t.INVALID_NUMBER)
        return

    order = await create_order(telegram_id=message.from_user.id, type="wallet_topup", amount=amount, status="awaiting_receipt")

    card = await get_round_robin_card()
    if not card:
        await message.answer(t.NO_ACTIVE_CARD, reply_markup=main_menu(message.from_user.id == ADMIN_TELEGRAM_ID))
        await state.clear()
        return

    await state.update_data(order_id=order.id, amount=amount, current_card_id=card.id)
    await state.set_state(TopUp.awaiting_receipt)
    await message.answer(
        t.PAYMENT_INSTRUCTIONS.format(amount=amount, card_number=card.card_number, holder_name=card.holder_name or ""),
        reply_markup=payment_keyboard(),
    )


@router.message(TopUp.awaiting_receipt, F.text == t.BTN_NEXT_CARD)
async def next_card_topup(message: Message, state: FSMContext):
    data = await state.get_data()
    card = await get_next_card(data.get("current_card_id"))
    if not card:
        await message.answer(t.NO_MORE_CARDS)
        return
    await state.update_data(current_card_id=card.id)
    await message.answer(
        t.PAYMENT_INSTRUCTIONS.format(amount=data["amount"], card_number=card.card_number, holder_name=card.holder_name or ""),
        reply_markup=payment_keyboard(),
    )


@router.message(TopUp.awaiting_receipt, F.photo)
async def receipt_photo(message: Message, state: FSMContext):
    await _handle_receipt(message, state, photo_file_id=message.photo[-1].file_id, text=message.caption)


@router.message(TopUp.awaiting_receipt, F.text)
async def receipt_text(message: Message, state: FSMContext):
    if message.text == t.BTN_NEXT_CARD:
        return
    await _handle_receipt(message, state, photo_file_id=None, text=message.text)


async def _handle_receipt(message: Message, state: FSMContext, photo_file_id: str | None, text: str | None):
    data = await state.get_data()
    order_id = data["order_id"]
    card = None
    if data.get("current_card_id"):
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
        order_type="شارژ کیف پول",
        user_display=user_display,
        telegram_id=message.from_user.id,
        deep_link=_deep_link(message.from_user),
        amount=data["amount"],
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
