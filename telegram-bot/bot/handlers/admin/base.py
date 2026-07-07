from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message

from ...config import is_admin


class AdminOnlyMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: TelegramObject, data):
        user = data.get("event_from_user")
        if user is None or not is_admin(user.id):
            if isinstance(event, Message):
                await event.answer( "شما به این بخش دسترسی ندارید. \n برای بازگشت به منوی اصلی. \n /start")
            return
        return await handler(event, data)
