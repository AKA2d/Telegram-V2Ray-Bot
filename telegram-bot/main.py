import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import TELEGRAM_BOT_TOKEN
from bot.db import init_db
from bot.handlers import account_info, admin_entry, buy_service, connect_guide, manage_service, start, wallet
from bot.handlers.admin import router as admin_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


async def main() -> None:
    # Ensure the database schema is created/updated before the bot starts.
    await init_db()

    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(start.router)
    dp.include_router(admin_entry.router)
    dp.include_router(buy_service.router)
    dp.include_router(wallet.router)
    dp.include_router(manage_service.router)
    dp.include_router(account_info.router)
    dp.include_router(connect_guide.router)
    dp.include_router(admin_router)

    logger.info("Starting bot polling...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
