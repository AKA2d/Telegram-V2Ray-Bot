from aiogram import Bot

from .config import REQUIRED_CHANNEL_ID


async def is_channel_member(bot: Bot, telegram_id: int) -> bool:
    if not REQUIRED_CHANNEL_ID:
        return True
    try:
        member = await bot.get_chat_member(REQUIRED_CHANNEL_ID, telegram_id)
        return member.status not in ("left", "kicked")
    except Exception:
        # If the bot can't check (not admin in channel, wrong id, etc.) don't block users.
        return True
