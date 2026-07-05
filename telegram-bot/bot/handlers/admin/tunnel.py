from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from ... import texts as t
from ...config import DIRECT_NODE_TAGS
from ...keyboards import admin_menu_keyboard, cancel_keyboard
from ...panel_client import PanelAPIError, panel_client
from ...states import AdminTunnel
from ...users_repo import all_user_ids
from ...services_repo import list_user_services
from .base import AdminOnlyMiddleware

router = Router(name="admin_tunnel")
router.message.middleware(AdminOnlyMiddleware())
router.callback_query.middleware(AdminOnlyMiddleware())

TUNNEL_TAG = "tunnel"


def _action_keyboard(target: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t.TUNNEL_ADDED.split(" ")[0] + " افزودن", callback_data=f"tunnel_add:{target}"),
                InlineKeyboardButton(text=t.TUNNEL_REMOVED.split(" ")[0] + " حذف", callback_data=f"tunnel_remove:{target}"),
            ]
        ]
    )


@router.message(F.text == t.ADMIN_MENU_TUNNEL)
async def start_tunnel(message: Message, state: FSMContext):
    await state.set_state(AdminTunnel.target)
    await message.answer(t.ASK_TUNNEL_TARGET, reply_markup=cancel_keyboard())


@router.message(AdminTunnel.target)
async def choose_tunnel_action(message: Message, state: FSMContext):
    target = message.text.strip()
    await state.clear()
    await message.answer(f"هدف: {target}", reply_markup=_action_keyboard(target))


async def _all_service_identifiers() -> list[str]:
    identifiers = []
    for telegram_id in await all_user_ids():
        for service in await list_user_services(telegram_id):
            identifiers.append(service.panel_uuid or service.panel_username)
    return identifiers


@router.callback_query(F.data.startswith("tunnel_add:"))
async def tunnel_add(callback: CallbackQuery):
    target = callback.data.split(":", 1)[1]
    targets = await _all_service_identifiers() if target == "همه" else [target]
    errors = 0
    for identifier in targets:
        try:
            await panel_client.add_tunnel_to_user(identifier, TUNNEL_TAG)
        except PanelAPIError:
            errors += 1
    msg = t.TUNNEL_ADDED if errors == 0 else f"{t.TUNNEL_ADDED} ({errors} خطا)"
    await callback.message.answer(msg, reply_markup=admin_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("tunnel_remove:"))
async def tunnel_remove(callback: CallbackQuery):
    target = callback.data.split(":", 1)[1]
    targets = await _all_service_identifiers() if target == "همه" else [target]
    errors = 0
    for identifier in targets:
        try:
            await panel_client.remove_tunnel_from_user(identifier, TUNNEL_TAG)
        except PanelAPIError:
            errors += 1
    msg = t.TUNNEL_REMOVED if errors == 0 else f"{t.TUNNEL_REMOVED} ({errors} خطا)"
    await callback.message.answer(msg, reply_markup=admin_menu_keyboard())
    await callback.answer()
