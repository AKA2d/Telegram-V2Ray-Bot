"""Catch-all handler for unrecognized text messages in the main menu.

This router MUST be included after all other routers so it only triggers
when no specific button handler matched.
"""

from aiogram import Router
from aiogram.fsm.state import default_state
from aiogram.types import Message

from .. import texts as t
from ..config import is_admin
from ..keyboards import main_menu
from ..wholesalers_repo import is_wholesaler

router = Router(name="fallback")


async def _user_menu(user_id: int):
    return main_menu(is_admin=is_admin(user_id), is_wholesaler=await is_wholesaler(user_id))


@router.message(default_state)
async def unknown_main_menu(message: Message):
    await message.answer(
        t.UNKNOWN_COMMAND,
        reply_markup=await _user_menu(message.from_user.id),
    )
