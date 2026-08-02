import asyncio

from aiogram import F, Router
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from ... import texts as t
from ...keyboards import admin_menu_keyboard, confirm_keyboard, cancel_keyboard
from ...states import AdminBroadcast
from ...users_repo import all_user_ids
from .base import AdminOnlyMiddleware

router = Router(name="admin_broadcast")
router.message.middleware(AdminOnlyMiddleware())


@router.message(F.text == t.ADMIN_MENU_BROADCAST)
async def start_broadcast(message: Message, state: FSMContext):
    await state.set_state(AdminBroadcast.waiting)
    await message.answer(t.ASK_BROADCAST_TEXT, reply_markup=cancel_keyboard())


@router.message(AdminBroadcast.waiting, F.media_group)
async def receive_album(message: Message, state: FSMContext, album: list[Message]):
    """Receive a media group (album) and store its message IDs for broadcast."""
    chat_id = message.chat.id
    message_ids = [m.message_id for m in album]

    await state.update_data(
        source_chat_id=chat_id,
        message_ids=message_ids,
        is_media_group=True,
    )
    count = len(await all_user_ids())
    await state.set_state(AdminBroadcast.confirm)
    await message.answer(
        t.BROADCAST_CONFIRM.format(count=count),
        reply_markup=confirm_keyboard(),
    )


@router.message(AdminBroadcast.waiting)
async def receive_single(message: Message, state: FSMContext):
    """Receive a single message (text, photo, video, forwarded, etc.) and store it."""
    chat_id = message.chat.id
    message_id = message.message_id

    await state.update_data(
        source_chat_id=chat_id,
        message_ids=[message_id],
        is_media_group=False,
    )
    count = len(await all_user_ids())
    await state.set_state(AdminBroadcast.confirm)
    await message.answer(
        t.BROADCAST_CONFIRM.format(count=count),
        reply_markup=confirm_keyboard(),
    )


async def _copy_to_user(bot, source_chat_id: int, message_ids: list[int], is_media_group: bool, user_id: int) -> None:
    """Copy the broadcast message(s) to a single user."""
    if is_media_group:
        await bot.copy_messages(chat_id=user_id, from_chat_id=source_chat_id, message_ids=message_ids)
    else:
        await bot.copy_message(chat_id=user_id, from_chat_id=source_chat_id, message_id=message_ids[0])


@router.message(AdminBroadcast.confirm, F.text == t.BTN_CONFIRM)
async def execute_broadcast(message: Message, state: FSMContext):
    data = await state.get_data()
    source_chat_id = data["source_chat_id"]
    message_ids = data["message_ids"]
    is_media_group = data["is_media_group"]
    await state.clear()

    user_ids = await all_user_ids()
    await message.answer(t.BROADCAST_STARTED, reply_markup=admin_menu_keyboard())

    sent = 0
    failed = 0
    for i, telegram_id in enumerate(user_ids, start=1):
        try:
            await _copy_to_user(message.bot, source_chat_id, message_ids, is_media_group, telegram_id)
            sent += 1
        except TelegramRetryAfter as exc:
            await asyncio.sleep(exc.retry_after)
            try:
                await _copy_to_user(message.bot, source_chat_id, message_ids, is_media_group, telegram_id)
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


@router.message(AdminBroadcast.confirm, F.text.in_({t.BTN_CANCEL, t.BTN_CANCEL_FLOW}))
async def cancel_broadcast(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(t.CANCELLED, reply_markup=admin_menu_keyboard())
