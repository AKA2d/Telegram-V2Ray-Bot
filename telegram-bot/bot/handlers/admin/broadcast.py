import asyncio

from aiogram import F, Router
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from ... import texts as t
from ...keyboards import admin_menu_keyboard, cancel_keyboard
from ...states import AdminBroadcast
from ...users_repo import all_user_ids
from .base import AdminOnlyMiddleware

router = Router(name="admin_broadcast")
router.message.middleware(AdminOnlyMiddleware())


@router.message(F.text == t.ADMIN_MENU_BROADCAST)
async def start_broadcast(message: Message, state: FSMContext):
    await state.set_state(AdminBroadcast.text)
    await message.answer(t.ASK_BROADCAST_TEXT, reply_markup=cancel_keyboard())


@router.message(AdminBroadcast.text)
async def run_broadcast(message: Message, state: FSMContext):
    text = message.text
    await state.clear()
    user_ids = await all_user_ids()
    await message.answer(t.BROADCAST_STARTED, reply_markup=admin_menu_keyboard())

    sent = 0
    failed = 0
    for i, telegram_id in enumerate(user_ids, start=1):
        try:
            await message.bot.send_message(telegram_id, text)
            sent += 1
        except TelegramRetryAfter as exc:
            await asyncio.sleep(exc.retry_after)
            try:
                await message.bot.send_message(telegram_id, text)
                sent += 1
            except Exception:
                failed += 1
        except TelegramForbiddenError:
            failed += 1
        except Exception:
            failed += 1

        if i % 25 == 0:
            await message.answer(t.BROADCAST_PROGRESS.format(sent=sent, total=len(user_ids), failed=failed))
        await asyncio.sleep(0.05)

    await message.answer(t.BROADCAST_DONE.format(sent=sent, total=len(user_ids)))
