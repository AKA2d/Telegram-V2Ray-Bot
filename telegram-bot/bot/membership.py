import logging

from aiogram import Bot

from .config import REQUIRED_CHANNEL_ID

logger = logging.getLogger(__name__)


async def is_channel_member(bot: Bot, telegram_id: int) -> bool:
    if not REQUIRED_CHANNEL_ID:
        return True
    try:
        member = await bot.get_chat_member(REQUIRED_CHANNEL_ID, telegram_id)
        return member.status not in ("left", "kicked")
    except Exception:
        # This is an access-control check. Failing open would let users bypass
        # the required channel when the bot loses channel-admin access.
        logger.exception("Unable to verify required-channel membership for %s", telegram_id)
        return False
