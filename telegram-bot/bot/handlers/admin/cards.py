from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from ... import texts as t
from ...cards_repo import add_card, list_cards, remove_card, set_active_card
from ...keyboards import admin_menu_keyboard, cancel_keyboard
from ...states import AdminCards
from .base import AdminOnlyMiddleware

router = Router(name="admin_cards")
router.message.middleware(AdminOnlyMiddleware())
router.callback_query.middleware(AdminOnlyMiddleware())


def _cards_keyboard(cards: list) -> InlineKeyboardMarkup:
    rows = []
    for c in cards:
        label = f"{'✅ ' if c.is_active else ''}{c.card_number} — {c.holder_name or ''}"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"card_activate:{c.id}")])
        rows.append([InlineKeyboardButton(text=f"🗑 حذف {c.card_number[-4:]}", callback_data=f"card_remove:{c.id}")])
    rows.append([InlineKeyboardButton(text="➕ افزودن کارت جدید", callback_data="card_add")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.message(F.text == t.ADMIN_MENU_CARDS)
async def show_cards(message: Message):
    cards = await list_cards()
    text = t.NO_CARDS if not cards else "کارت‌های ثبت‌شده:"
    await message.answer(text, reply_markup=_cards_keyboard(cards))


@router.callback_query(F.data == "card_add")
async def prompt_add_card(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminCards.add_number)
    await callback.message.answer(t.ASK_CARD_NUMBER, reply_markup=cancel_keyboard())
    await callback.answer()


@router.message(AdminCards.add_number)
async def set_card_number(message: Message, state: FSMContext):
    await state.update_data(card_number=message.text.strip())
    await state.set_state(AdminCards.add_holder)
    await message.answer(t.ASK_CARD_HOLDER)


@router.message(AdminCards.add_holder)
async def set_card_holder(message: Message, state: FSMContext):
    data = await state.get_data()
    await add_card(data["card_number"], message.text.strip())
    await state.clear()
    await message.answer(t.CARD_ADDED, reply_markup=admin_menu_keyboard())


@router.callback_query(F.data.startswith("card_activate:"))
async def activate_card(callback: CallbackQuery):
    card_id = int(callback.data.split(":")[1])
    await set_active_card(card_id)
    cards = await list_cards()
    await callback.message.edit_text(t.CARD_ACTIVATED, reply_markup=_cards_keyboard(cards))
    await callback.answer()


@router.callback_query(F.data.startswith("card_remove:"))
async def remove_card_cb(callback: CallbackQuery):
    card_id = int(callback.data.split(":")[1])
    await remove_card(card_id)
    cards = await list_cards()
    await callback.message.edit_text(t.CARD_REMOVED, reply_markup=_cards_keyboard(cards))
    await callback.answer()
