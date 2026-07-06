from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import CallbackQuery, Message

from .. import texts as t
from ..keyboards import service_actions_keyboard, services_list_keyboard
from ..panel_client import PanelAPIError, panel_client
from ..services_repo import find_service_by_link_or_uuid, get_service, list_user_services, update_service

router = Router(name="manage_service")


def _format_service(service) -> str:
    return t.SERVICE_DETAIL.format(
        id=service.id,
        status=service.status,
        user_count=service.user_count,
        months=service.months,
        traffic_gb=service.traffic_gb,
        created_at=service.created_at.strftime("%Y-%m-%d") if service.created_at else "-",
        link=service.subscription_link or "—",
    )


@router.message(F.text == t.MAIN_MENU_MANAGE)
async def manage_menu(message: Message):
    services = await list_user_services(message.from_user.id)
    if not services:
        await message.answer(t.NO_SERVICES)
        return
    await message.answer(t.MANAGE_SERVICE_PROMPT, reply_markup=services_list_keyboard(services))


@router.callback_query(F.data.startswith("svc_view:"))
async def view_service(callback: CallbackQuery):
    service_id = int(callback.data.split(":")[1])
    service = await get_service(service_id)
    if not service or service.owner_telegram_id != callback.from_user.id:
        await callback.answer(t.SERVICE_NOT_FOUND, show_alert=True)
        return
    await callback.message.answer(_format_service(service), reply_markup=service_actions_keyboard(service.id))
    await callback.answer()


@router.callback_query(F.data.startswith("svc_regen:"))
async def regenerate_service(callback: CallbackQuery):
    service_id = int(callback.data.split(":")[1])
    service = await get_service(service_id)
    if not service or service.owner_telegram_id != callback.from_user.id:
        await callback.answer(t.SERVICE_NOT_FOUND, show_alert=True)
        return
    try:
        panel_user = await panel_client.regenerate_subscription(service.panel_uuid or service.panel_username)
    except PanelAPIError:
        await callback.answer(t.ERROR_GENERIC, show_alert=True)
        return
    await update_service(service.id, subscription_link=panel_user.subscription_link, panel_uuid=panel_user.uuid or service.panel_uuid)
    await callback.message.answer(t.REGENERATE_DONE.format(link=panel_user.subscription_link or "—"))
    await callback.answer()


@router.callback_query(F.data.startswith("svc_increase:"))
@router.callback_query(F.data.startswith("svc_extend:"))
async def phase2_not_available(callback: CallbackQuery):
    await callback.answer(t.PHASE2_NOT_AVAILABLE, show_alert=True)


@router.message(default_state, F.text.regexp(r"^[A-Za-z0-9\-_:/.]{6,}$"))
async def lookup_by_text(message: Message):
    service = await find_service_by_link_or_uuid(message.text.strip())
    if not service or service.owner_telegram_id != message.from_user.id:
        return
    await message.answer(_format_service(service), reply_markup=service_actions_keyboard(service.id))
