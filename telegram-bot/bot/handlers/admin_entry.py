from aiogram import F, Router
from aiogram.types import Message

from .. import texts as t
from ..config import is_admin
from ..keyboards import admin_menu_keyboard, main_menu
from ..settings_repo import get_setting, set_setting

router = Router(name="admin_entry")


@router.message(F.text == t.ADMIN_MENU)
async def open_admin_menu(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer(t.NOT_AUTHORIZED, reply_markup=main_menu(False))
        return
    sales_closed = (await get_setting("sales_closed")) == "1"
    await message.answer(t.ADMIN_MENU, reply_markup=admin_menu_keyboard(sales_closed))


@router.message(F.text == t.SALES_CLOSED_LABEL_ON)
@router.message(F.text == t.SALES_CLOSED_LABEL_OFF)
async def toggle_sales(message: Message):
    if not is_admin(message.from_user.id):
        return
    sales_closed = (await get_setting("sales_closed")) == "1"
    new_value = "0" if sales_closed else "1"
    await set_setting("sales_closed", new_value)
    now_closed = new_value == "1"
    text = t.SALES_CLOSED_ON if now_closed else t.SALES_CLOSED_OFF
    await message.answer(text, reply_markup=admin_menu_keyboard(now_closed))
