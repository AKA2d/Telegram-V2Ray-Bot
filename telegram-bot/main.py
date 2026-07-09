import asyncio
import logging
import ssl
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Update

from bot.config import (
    TELEGRAM_BOT_TOKEN,
    WEBHOOK_HOST,
    WEBHOOK_MODE,
    WEBHOOK_PATH,
    WEBHOOK_PORT,
    WEBHOOK_SECRET,
)
from bot.db import init_db
from bot.handlers import (
    account_info,
    admin_entry,
    buy_service,
    connect_guide,
    manage_service,
    start,
    wallet,
)
from bot.handlers.admin import router as admin_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def _setup_handlers(dp: Dispatcher) -> None:
    dp.include_router(start.router)
    dp.include_router(admin_entry.router)
    dp.include_router(buy_service.router)
    dp.include_router(wallet.router)
    dp.include_router(manage_service.router)
    dp.include_router(account_info.router)
    dp.include_router(connect_guide.router)
    dp.include_router(admin_router)


async def _run_polling(bot: Bot, dp: Dispatcher) -> None:
    logger.info("Starting bot in polling mode...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


async def _run_webhook(bot: Bot, dp: Dispatcher) -> None:
    if not WEBHOOK_HOST:
        raise RuntimeError("WEBHOOK_HOST is required when WEBHOOK_MODE=true")

    webhook_url = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
    logger.info("Setting webhook URL: %s", webhook_url)

    await bot.set_webhook(
        webhook_url,
        secret_token=WEBHOOK_SECRET or None,
        drop_pending_updates=True,
    )

    app = web.Application()
    app["bot"] = bot
    app["dp"] = dp

    async def handle_webhook(request: web.Request) -> web.Response:
        if WEBHOOK_SECRET:
            secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
            if secret != WEBHOOK_SECRET:
                return web.Response(status=403)
        bot: Bot = request.app["bot"]
        dp: Dispatcher = request.app["dp"]
        update = Update.model_validate(await request.json())
        await dp.feed_update(bot, update)
        return web.Response()

    app.router.add_post(WEBHOOK_PATH, handle_webhook)


    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.load_cert_chain(
        '/etc/letsencrypt/live/tgx.tbx.ncmc.ir/fullchain.pem',
        '/etc/letsencrypt/live/tgx.tbx.ncmc.ir/privkey.pem'
    )
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", WEBHOOK_PORT, ssl_context=ssl_context)
    await site.start()
    logger.info("Webhook server listening on port %d", WEBHOOK_PORT)

    try:
        await asyncio.Event().wait()
    finally:
        await runner.cleanup()


async def main() -> None:
    await init_db()

    session = AiohttpSession()
    bot = Bot(token=TELEGRAM_BOT_TOKEN, session=session)
    dp = Dispatcher(storage=MemoryStorage())

    _setup_handlers(dp)

    if WEBHOOK_MODE:
        await _run_webhook(bot, dp)
    else:
        await _run_polling(bot, dp)


if __name__ == "__main__":
    asyncio.run(main())
