import asyncio
import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from ... import texts as t
from ...keyboards import admin_menu_keyboard, confirm_keyboard, cancel_keyboard
from ...states import AdminBroadcast
from ...users_repo import all_user_ids
from .base import AdminOnlyMiddleware

router = Router(name="admin_broadcast")
router.message.middleware(AdminOnlyMiddleware())
logger = logging.getLogger(__name__)

# Buffer: collect messages for a short window before finalising.
_pending_broadcast_tasks: dict[tuple[int, int], asyncio.Task] = {}
_pending_broadcasts: dict[tuple[int, int], dict] = {}

_BUFFER_DELAY = 2.0


@router.message(F.text == t.ADMIN_MENU_BROADCAST)
async def start_broadcast(message: Message, state: FSMContext):
    task_key = (message.chat.id, message.from_user.id)
    old_task = _pending_broadcast_tasks.pop(task_key, None)
    if old_task:
        old_task.cancel()
    _pending_broadcasts.pop(task_key, None)

    await state.set_state(AdminBroadcast.waiting)
    await message.answer(t.ASK_BROADCAST_TEXT, reply_markup=cancel_keyboard())


async def _finalize_buffered(state: FSMContext, bot, task_key: tuple[int, int], buf: dict) -> None:
    """After a quiet period, commit the buffered message ids to state."""
    try:
        await asyncio.sleep(_BUFFER_DELAY)
        if _pending_broadcasts.get(task_key) is not buf:
            return

        chat_id = buf["chat_id"]
        message_ids = sorted(buf["message_ids"])
        has_media_group = buf.get("media_group_id") is not None
        logger.info(
            "Broadcast buffer finalized: chat=%s count=%d has_album=%s ids=%s",
            chat_id, len(message_ids), has_media_group, message_ids,
        )

        if not message_ids:
            return

        await state.update_data(
            source_chat_id=chat_id,
            message_ids=message_ids,
            use_group=has_media_group or len(message_ids) > 1,
        )
        await state.set_state(AdminBroadcast.confirm)
        count = len(await all_user_ids())
        await bot.send_message(
            chat_id,
            t.BROADCAST_CONFIRM.format(count=count),
            reply_markup=confirm_keyboard(),
        )
    except Exception:
        logger.exception("Failed to finalize broadcast buffer")
        await bot.send_message(task_key[0], "دریافت پیام ناموفق بود. لطفاً دوباره تلاش کنید.")
    finally:
        if _pending_broadcast_tasks.get(task_key) is asyncio.current_task():
            _pending_broadcast_tasks.pop(task_key, None)
            _pending_broadcasts.pop(task_key, None)


@router.message(AdminBroadcast.waiting)
async def receive_message(message: Message, state: FSMContext):
    """Buffer every message for a short window so multi-message forwards / albums are captured."""
    chat_id = message.chat.id
    user_id = message.from_user.id
    task_key = (chat_id, user_id)

    # --- album path: same media_group_id → append immediately ---
    if message.media_group_id:
        buf = _pending_broadcasts.get(task_key)
        if buf is None or buf.get("media_group_id") != message.media_group_id:
            buf = {"chat_id": chat_id, "media_group_id": message.media_group_id, "message_ids": []}
            _pending_broadcasts[task_key] = buf
        buf["message_ids"].append(message.message_id)
    else:
        # --- single / forwarded path ---
        buf = _pending_broadcasts.get(task_key)
        if buf is None:
            buf = {"chat_id": chat_id, "media_group_id": None, "message_ids": []}
            _pending_broadcasts[task_key] = buf
        buf["message_ids"].append(message.message_id)

    # Reset the finalization timer each time a new message arrives.
    old = _pending_broadcast_tasks.pop(task_key, None)
    if old:
        old.cancel()
    _pending_broadcast_tasks[task_key] = asyncio.create_task(
        _finalize_buffered(state, message.bot, task_key, buf)
    )


async def _send_to_user(bot, source_chat_id: int, message_ids: list[int], use_group: bool, user_id: int) -> None:
    """Send the broadcast message(s) to a single user.

    Uses ``copy_messages`` which preserves media group structure and captions
    but does NOT show the original sender's name (unlike forward_messages).
    """
    if use_group and len(message_ids) > 1:
        await bot.copy_messages(
            chat_id=user_id,
            from_chat_id=source_chat_id,
            message_ids=message_ids,
        )
    else:
        await bot.copy_message(
            chat_id=user_id,
            from_chat_id=source_chat_id,
            message_id=message_ids[0],
        )


@router.message(AdminBroadcast.confirm, F.text == t.BTN_CONFIRM)
async def execute_broadcast(message: Message, state: FSMContext):
    data = await state.get_data()
    source_chat_id = data["source_chat_id"]
    message_ids = data["message_ids"]
    use_group = data.get("use_group", False)
    await state.clear()

    user_ids = await all_user_ids()
    await message.answer(t.BROADCAST_STARTED, reply_markup=admin_menu_keyboard())

    sent = 0
    failed = 0
    for i, telegram_id in enumerate(user_ids, start=1):
        try:
            await _send_to_user(message.bot, source_chat_id, message_ids, use_group, telegram_id)
            sent += 1
        except TelegramRetryAfter as exc:
            await asyncio.sleep(exc.retry_after)
            try:
                await _send_to_user(message.bot, source_chat_id, message_ids, use_group, telegram_id)
                sent += 1
            except Exception:
                failed += 1
        except (TelegramForbiddenError, TelegramBadRequest):
            failed += 1
        except Exception:
            logger.exception("Failed to send broadcast to %s", telegram_id)
            failed += 1

        if i % 25 == 0:
            await message.answer(t.BROADCAST_PROGRESS.format(sent=sent, total=len(user_ids), failed=failed))
        await asyncio.sleep(0.05)

    await message.answer(t.BROADCAST_DONE.format(sent=sent, total=len(user_ids)))


@router.message(AdminBroadcast.confirm, F.text.in_({t.BTN_CANCEL, t.BTN_CANCEL_FLOW}))
async def cancel_broadcast(message: Message, state: FSMContext):
    task_key = (message.chat.id, message.from_user.id)
    old_task = _pending_broadcast_tasks.pop(task_key, None)
    if old_task:
        old_task.cancel()
    _pending_broadcasts.pop(task_key, None)

    await state.clear()
    await message.answer(t.CANCELLED, reply_markup=admin_menu_keyboard())
