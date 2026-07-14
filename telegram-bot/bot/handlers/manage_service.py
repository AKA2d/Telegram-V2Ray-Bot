from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import CallbackQuery, Message

from .. import texts as t
from ..keyboards import service_actions_keyboard, services_list_keyboard
from ..panel_client import PanelAPIError, panel_client
from ..services_repo import find_service_by_link_or_uuid, get_service, list_user_services, update_service

router = Router(name="manage_service")


def _format_remaining_days(expires_at) -> str:
    if not expires_at:
        return "نامحدود"
    now = datetime.now(timezone.utc)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    delta = expires_at - now
    days = delta.days
    if days <= 0:
        return "منقضی شده"
    return f"{days} روز"


def _format_traffic(bytes_used: int | None, total_gb: int) -> str:
    if bytes_used is None:
        return f"{total_gb} گیگ (نامشخص)"
    used_gb = bytes_used / (1024 ** 3)
    remaining = total_gb - used_gb
    if remaining < 0:
        remaining = 0
    return f"{remaining:.1f} از {total_gb} گیگ"


async def _format_service(service) -> str:
    remaining_days = _format_remaining_days(service.expires_at)

    remaining_traffic = f"{service.traffic_gb} گیگ"
    if service.status == "active":
        try:
            panel_user = await panel_client.get_user(service.panel_username)
            bytes_used = panel_user.raw.get("usage") or panel_user.raw.get("data_usage") or panel_user.raw.get("used_traffic")
            if bytes_used:
                remaining_traffic = _format_traffic(bytes_used, service.traffic_gb)
        except PanelAPIError:
            pass

    link = service.subscription_link or "—"
    if service.status != "active":
        link = "غیرفعال"

    return t.SERVICE_DETAIL.format(
        id=service.id,
        panel_username=service.panel_username,
        months=service.months,
        traffic_gb=service.traffic_gb,
        status=service.status,
        remaining_days=remaining_days,
        remaining_traffic=remaining_traffic,
        created_at=service.created_at.strftime("%Y-%m-%d") if service.created_at else "-",
        expires_at=service.expires_at.strftime("%Y-%m-%d") if service.expires_at else "نامحدود",
        link=link,
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
    await callback.message.answer(await _format_service(service), reply_markup=service_actions_keyboard(service.id))
    await callback.answer()


@router.callback_query(F.data.startswith("svc_regen:"))
async def regenerate_service(callback: CallbackQuery):
    service_id = int(callback.data.split(":")[1])
    service = await get_service(service_id)
    if not service or service.owner_telegram_id != callback.from_user.id:
        await callback.answer(t.SERVICE_NOT_FOUND, show_alert=True)
        return
    if service.status != "active":
        await callback.answer("سرویس فعال نیست.", show_alert=True)
        return
    try:
        panel_user = await panel_client.regenerate_subscription(service.panel_uuid or service.panel_username)
    except PanelAPIError:
        await callback.answer(t.ERROR_GENERIC, show_alert=True)
        return
    await update_service(service.id, subscription_link=panel_user.subscription_link, panel_uuid=panel_user.uuid or service.panel_uuid)
    if panel_user.subscription_link:
        from ..qr_gen import generate_qr_image
        text = t.REGENERATE_DONE.format(link=panel_user.subscription_link)
        qr_photo = generate_qr_image(panel_user.subscription_link)
        await callback.message.answer_photo(qr_photo, caption=text)
    else:
        await callback.message.answer(t.REGENERATE_DONE.format(link="—"))
    await callback.answer()


@router.callback_query(F.data.startswith("svc_qr:"))
async def get_qr_code(callback: CallbackQuery):
    service_id = int(callback.data.split(":")[1])
    service = await get_service(service_id)
    if not service or service.owner_telegram_id != callback.from_user.id:
        await callback.answer(t.SERVICE_NOT_FOUND, show_alert=True)
        return
    if not service.subscription_link:
        await callback.answer("لینک اشتراک وجود ندارد.", show_alert=True)
        return
    if service.status != "active":
        await callback.answer("سرویس فعال نیست.", show_alert=True)
        return
    from ..qr_gen import generate_qr_image
    qr_photo = generate_qr_image(service.subscription_link)
    await callback.message.answer_photo(qr_photo, caption="📱 QR Code لینک اشتراک")
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
    await message.answer(await _format_service(service), reply_markup=service_actions_keyboard(service.id))
