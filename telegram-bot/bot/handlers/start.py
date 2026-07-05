from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from .. import texts as t
from ..config import ADMIN_TELEGRAM_ID, REQUIRED_CHANNEL_ID
from ..keyboards import join_channel_keyboard, main_menu
from ..membership import is_channel_member
from ..users_repo import get_or_create_user

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await get_or_create_user(message.from_user.id, message.from_user.username, message.from_user.first_name)

    if REQUIRED_CHANNEL_ID and not await is_channel_member(message.bot, message.from_user.id):
        await message.answer(t.JOIN_CHANNEL_PROMPT, reply_markup=join_channel_keyboard(REQUIRED_CHANNEL_ID))
        return

    is_admin = message.from_user.id == ADMIN_TELEGRAM_ID
    await message.answer(t.WELCOME, reply_markup=main_menu(is_admin))


@router.callback_query(F.data == "check_membership")
async def check_membership(callback: CallbackQuery):
    if await is_channel_member(callback.bot, callback.from_user.id):
        is_admin = callback.from_user.id == ADMIN_TELEGRAM_ID
        await callback.message.answer(t.WELCOME, reply_markup=main_menu(is_admin))
        await callback.answer()
    else:
        await callback.answer(t.NOT_MEMBER_YET, show_alert=True)


@router.message(F.text == t.BTN_BACK)
async def back_to_main(message: Message, state: FSMContext):
    await state.clear()
    is_admin = message.from_user.id == ADMIN_TELEGRAM_ID
    await message.answer(t.WELCOME, reply_markup=main_menu(is_admin))


@router.message(F.text == t.BTN_CANCEL_FLOW)
async def cancel_flow(message: Message, state: FSMContext):
    await state.clear()
    is_admin = message.from_user.id == ADMIN_TELEGRAM_ID
    await message.answer(t.CANCELLED, reply_markup=main_menu(is_admin))
