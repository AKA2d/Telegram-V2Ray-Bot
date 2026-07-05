from aiogram import F, Router
from aiogram.exceptions import TelegramForbiddenError
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from ... import texts as t
from ...keyboards import admin_menu_keyboard, cancel_keyboard
from ...states import AdminDirectMessage
from ...users_repo import find_user
from .base import AdminOnlyMiddleware

router = Router(name="admin_direct")
router.message.middleware(AdminOnlyMiddleware())


@router.message(F.text == t.ADMIN_MENU_DIRECT)
async def start_direct(message: Message, state: FSMContext):
    await state.set_state(AdminDirectMessage.target)
    await message.answer(t.ASK_DIRECT_TARGET, reply_markup=cancel_keyboard())


@router.message(AdminDirectMessage.target)
async def set_direct_target(message: Message, state: FSMContext):
    user = await find_user(message.text.strip())
    if not user:
        await message.answer(t.CUSTOMER_NOT_FOUND, reply_markup=admin_menu_keyboard())
        await state.clear()
        return
    await state.update_data(target_telegram_id=user.telegram_id)
    await state.set_state(AdminDirectMessage.text)
    await message.answer(t.ASK_DIRECT_TEXT, reply_markup=cancel_keyboard())


@router.message(AdminDirectMessage.text)
async def send_direct(message: Message, state: FSMContext):
    data = await state.get_data()
    try:
        await message.bot.send_message(data["target_telegram_id"], message.text)
        await message.answer(t.DIRECT_MESSAGE_SENT, reply_markup=admin_menu_keyboard())
    except TelegramForbiddenError:
        await message.answer(t.DIRECT_MESSAGE_FAILED, reply_markup=admin_menu_keyboard())
    await state.clear()
