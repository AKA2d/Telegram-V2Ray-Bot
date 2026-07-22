from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from .. import texts as t
from ..config import is_admin
from ..keyboards import admin_menu_keyboard, cancel_keyboard, guide_management_keyboard, main_menu
from ..panel_client import PanelAPIError, panel_client
from ..services_repo import count_all_services
from ..settings_repo import get_setting, set_setting
from ..stats_repo import get_period_stats

router = Router(name="admin_entry")


@router.message(F.text == t.ADMIN_MENU)
async def open_admin_menu(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer(t.NOT_AUTHORIZED, reply_markup=main_menu(False))
        return
    sales_closed = (await get_setting("sales_closed")) == "1"
    await message.answer(t.ADMIN_MENU, reply_markup=admin_menu_keyboard(sales_closed))


@router.message(F.text == t.SALES_CLOSED_LABEL_ON)
@router.message(F.text == t.SALES_CLOSED_LABEL_OFF)
async def toggle_sales(message: Message):
    if not is_admin(message.from_user.id):
        return
    sales_closed = (await get_setting("sales_closed")) == "1"
    new_value = "0" if sales_closed else "1"
    await set_setting("sales_closed", new_value)
    now_closed = new_value == "1"
    text = t.SALES_CLOSED_ON if now_closed else t.SALES_CLOSED_OFF
    await message.answer(text, reply_markup=admin_menu_keyboard(now_closed))


@router.message(F.text == t.ADMIN_MENU_STATS)
async def show_stats(message: Message):
    if not is_admin(message.from_user.id):
        return
    total_users = active_users = disabled_users = online_users = limited_users = expired_users = "نامشخص"
    used_traffic = panel_total_traffic = "نامشخص"
    try:
        stats = await panel_client.get_system_stats()
        total_users = stats.get("total_user", 0)
        active_users = stats.get("active_users", 0)
        disabled_users = stats.get("disabled_users", 0)
        online_users = stats.get("online_users", 0)
        limited_users = stats.get("limited_users", 0)
        expired_users = stats.get("expired_users", 0)

        incoming = stats.get("incoming_bandwidth", 0)
        outgoing = stats.get("outgoing_bandwidth", 0)
        total_used = incoming + outgoing
        if total_used:
            used_gb = total_used / (1024**3)
            used_traffic = f"{used_gb / 1024:.1f} ترابایت" if used_gb >= 1024 else f"{used_gb:.1f} گیگابایت"

        admin_stats = await panel_client.get_admin_stats()
        total_traffic = admin_stats.get("data_limit", 0)
        if total_traffic:
            tg = total_traffic / (1024**3)
            panel_total_traffic = f"{tg / 1024:.1f} ترابایت" if tg >= 1024 else f"{tg:.1f} گیگابایت"
    except PanelAPIError:
        pass

    sold_amount = await get_setting("sold_amount")
    sold_traffic = await get_setting("sold_traffic")
    wholesaler_fee = await get_setting("wholesaler_fee")
    service_count = await count_all_services()
    period = await get_period_stats()

    await message.answer(
        t.PANEL_STATS.format(
            total_users=total_users,
            active_users=active_users,
            disabled_users=disabled_users,
            online_users=online_users,
            limited_users=limited_users,
            expired_users=expired_users,
            panel_total_traffic=panel_total_traffic,
            used_traffic=used_traffic,
            daily_amount=period["daily_amount"],
            daily_traffic=period["daily_traffic"],
            weekly_amount=period["weekly_amount"],
            weekly_traffic=period["weekly_traffic"],
            monthly_amount=period["monthly_amount"],
            monthly_traffic=period["monthly_traffic"],
            sold_amount=f"{int(sold_amount):,}",
            sold_traffic=sold_traffic,
            service_count=service_count,
            wholesaler_fee=f"{int(wholesaler_fee):,}",
        ),
        reply_markup=admin_menu_keyboard(),
    )


@router.message(F.text == t.ADMIN_MENU_TEST)
async def open_test_menu(message: Message):
    from .admin.test_mgmt import _show_test_settings
    await _show_test_settings(message)


@router.message(F.text == "📖 مدیریت راهنماها")
async def open_guide_menu(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("مدیریت راهنماها:", reply_markup=guide_management_keyboard())


# ---- Wholesaler fee management ----

_pending_fee_admins: set[int] = set()


@router.message(F.text == "💰 تنظیم هزینه عمده‌فروش")
async def prompt_set_wholesaler_fee(message: Message):
    if not is_admin(message.from_user.id):
        return
    _pending_fee_admins.add(message.from_user.id)
    current = await get_setting("wholesaler_fee")
    await message.answer(f"هزینه فعلی عمده‌فروشی: {int(current):,} تومان\n\nمبلغ جدید را وارد کنید:", reply_markup=cancel_keyboard())


@router.message(F.text.regexp(r"^\d+$"))
async def try_set_wholesaler_fee(message: Message):
    if message.from_user.id not in _pending_fee_admins:
        return
    if not is_admin(message.from_user.id):
        return
    _pending_fee_admins.discard(message.from_user.id)
    value = int(message.text.strip())
    if value <= 0:
        await message.answer(t.INVALID_NUMBER, reply_markup=admin_menu_keyboard())
        return
    await set_setting("wholesaler_fee", str(value))
    await message.answer(f"هزینه عمده‌فروشی به {value:,} تومان تغییر کرد.", reply_markup=admin_menu_keyboard())
