"""Globally enforce the optional required-channel membership rule."""

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from . import texts as t
from .config import REQUIRED_CHANNEL_ID, is_admin
from .keyboards import join_channel_keyboard
from .membership import is_channel_member


class RequiredChannelMiddleware(BaseMiddleware):
    """Block every customer update until the user has joined the channel."""

    @staticmethod
    def _is_exempt(event: TelegramObject) -> bool:
        if isinstance(event, Message):
            return bool(event.text and event.text.startswith("/start"))
        if isinstance(event, CallbackQuery):
            return event.data == "check_membership"
        return False

    async def __call__(self, handler, event: TelegramObject, data):
        if not REQUIRED_CHANNEL_ID or self._is_exempt(event):
            return await handler(event, data)

        user = data.get("event_from_user")
        if user is None or is_admin(user.id) or await is_channel_member(data["bot"], user.id):
            return await handler(event, data)

        if isinstance(event, Message):
            await event.answer(t.JOIN_CHANNEL_PROMPT, reply_markup=join_channel_keyboard(REQUIRED_CHANNEL_ID))
        elif isinstance(event, CallbackQuery):
            await event.answer(t.NOT_MEMBER_YET, show_alert=True)
            await event.message.answer(t.JOIN_CHANNEL_PROMPT, reply_markup=join_channel_keyboard(REQUIRED_CHANNEL_ID))
        return None
