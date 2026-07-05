from aiogram import F, Router
from aiogram.types import Message

from .. import texts as t
from ..config import ADMIN_TELEGRAM_ID
from ..keyboards import admin_menu_keyboard, main_menu

router = Router(name="admin_entry")


@router.message(F.text == t.ADMIN_MENU)
async def open_admin_menu(message: Message):
    if message.from_user.id != ADMIN_TELEGRAM_ID:
        await message.answer(t.NOT_AUTHORIZED, reply_markup=main_menu(False))
        return
    await message.answer(t.ADMIN_MENU, reply_markup=admin_menu_keyboard())
