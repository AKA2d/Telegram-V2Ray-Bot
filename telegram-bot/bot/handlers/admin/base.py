from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message

from ...config import ADMIN_TELEGRAM_ID


class AdminOnlyMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: TelegramObject, data):
        user = data.get("event_from_user")
        if user is None or user.id != ADMIN_TELEGRAM_ID:
            if isinstance(event, Message):
                await event.answer("شما به این بخش دسترسی ندارید.")
            return
        return await handler(event, data)
