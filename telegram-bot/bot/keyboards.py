from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

from . import texts as t


SUPPORT_USERNAME = "GodVPN_admin"


def main_menu(is_admin: bool = False) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text=t.MAIN_MENU_BUY), KeyboardButton(text=t.MAIN_MENU_MANAGE)],
        [KeyboardButton(text=t.MAIN_MENU_ACCOUNT), KeyboardButton(text=t.MAIN_MENU_TOPUP)],
        [KeyboardButton(text=t.MAIN_MENU_CONNECT)],
        [KeyboardButton(text=t.MAIN_MENU_SUPPORT)],
    ]
    if is_admin:
        rows.append([KeyboardButton(text=t.ADMIN_MENU)])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=t.BTN_CANCEL_FLOW)]], resize_keyboard=True)


def confirm_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t.BTN_CONFIRM), KeyboardButton(text=t.BTN_CANCEL)]],
        resize_keyboard=True,
    )


def join_channel_keyboard(channel_id: str) -> InlineKeyboardMarkup:
    link = channel_id if channel_id.startswith("http") else f"https://t.me/{channel_id.lstrip('@')}"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t.JOIN_CHANNEL_BUTTON, url=link)],
            [InlineKeyboardButton(text=t.CHECK_MEMBERSHIP_BUTTON, callback_data="check_membership")],
        ]
    )


def payment_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t.BTN_NEXT_CARD)], [KeyboardButton(text=t.BTN_CANCEL_FLOW)]],
        resize_keyboard=True,
    )


def order_review_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t.BTN_APPROVE, callback_data=f"order_approve:{order_id}"),
                InlineKeyboardButton(text=t.BTN_REJECT, callback_data=f"order_reject:{order_id}"),
            ]
        ]
    )


def service_actions_keyboard(service_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t.BTN_REGENERATE, callback_data=f"svc_regen:{service_id}")],
            [InlineKeyboardButton(text="📱 دریافت QR Code", callback_data=f"svc_qr:{service_id}")],
            [InlineKeyboardButton(text=t.BTN_EXTEND, callback_data=f"svc_extend:{service_id}")],
        ]
    )


def services_list_keyboard(services: list) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"#{s.id} — {s.panel_username} ({s.status})", callback_data=f"svc_view:{s.id}")] for s in services
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_menu_keyboard(sales_closed: bool | None = None) -> ReplyKeyboardMarkup:
    if sales_closed is None:
        import asyncio
        from .settings_repo import get_setting
        try:
            loop = asyncio.get_running_loop()
            # We're inside an async context, use a sync wrapper
            sales_closed = False
        except RuntimeError:
            sales_closed = False
    status_text = t.SALES_CLOSED_LABEL_OFF if sales_closed else t.SALES_CLOSED_LABEL_ON
    rows = [
        [KeyboardButton(text=t.ADMIN_MENU_ORDERS), KeyboardButton(text=t.ADMIN_MENU_PLANS)],
        [KeyboardButton(text=t.ADMIN_MENU_CUSTOMERS), KeyboardButton(text=t.ADMIN_MENU_WALLET)],
        [KeyboardButton(text=t.ADMIN_MENU_BROADCAST), KeyboardButton(text=t.ADMIN_MENU_DIRECT)],
        [KeyboardButton(text=t.ADMIN_MENU_CARDS), KeyboardButton(text=t.ADMIN_MENU_TUNNEL)],
        [KeyboardButton(text=t.ADMIN_MENU_WHOLESALERS), KeyboardButton(text=t.ADMIN_MENU_STATS)],
        [KeyboardButton(text=status_text)],
        [KeyboardButton(text=t.BTN_BACK)],
    ]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def plans_list_keyboard(plans: list, is_wholesaler: bool = False) -> InlineKeyboardMarkup:
    rows = []
    for i, p in enumerate(plans, 1):
        rows.append([InlineKeyboardButton(text=str(i), callback_data=f"plan_select:plan:{p.id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def format_plans_list(plans: list, is_wholesaler: bool = False) -> str:
    lines = [t.CHOOSE_PLAN_PROMPT, ""]
    for i, p in enumerate(plans, 1):
        price = p.wholesale_price if is_wholesaler and p.wholesale_price else p.price
        lines.append(f"{i}. {p.name} — {int(price)} تومان")
    return "\n".join(lines)


def plan_confirm_keyboard(plan_type: str, plan_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t.CONFIRM_YES, callback_data=f"plan_confirm:{plan_type}:{plan_id}")],
            [InlineKeyboardButton(text=t.CONFIRM_NO, callback_data="plan_cancel")],
        ]
    )


def admin_plans_keyboard(plans: list) -> InlineKeyboardMarkup:
    rows = []
    for i, p in enumerate(plans, 1):
        status = "✅" if p.is_active else "🚫"
        rows.append([InlineKeyboardButton(text=f"{i}. {status}", callback_data=f"plan_toggle:{p.id}")])
        rows.append([
            InlineKeyboardButton(text=f"✏️", callback_data=f"plan_edit:{p.id}"),
            InlineKeyboardButton(text=f"🗑", callback_data=f"plan_remove:{p.id}"),
        ])
    rows.append([InlineKeyboardButton(text="➕ افزودن پلن جدید", callback_data="plan_add")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def format_admin_plans_list(plans: list) -> str:
    if not plans:
        return t.NO_PLANS_DEFINED
    lines = [t.PLANS_LIST_HEADER, ""]
    for i, p in enumerate(plans, 1):
        status = "✅" if p.is_active else "🚫"
        wholesale_info = f" / عمده: {int(p.wholesale_price)}" if p.wholesale_price else ""
        lines.append(f"{i}. {status} {p.name} — {p.months} ماه / {p.traffic_gb} گیگ / {int(p.price)} تومان{wholesale_info}")
    return "\n".join(lines)


def plan_edit_field_keyboard(plan_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="نام", callback_data=f"plan_edit_field:{plan_id}:name")],
            [InlineKeyboardButton(text="تعداد کاربر", callback_data=f"plan_edit_field:{plan_id}:user_count")],
            [InlineKeyboardButton(text="مدت (ماه)", callback_data=f"plan_edit_field:{plan_id}:months")],
            [InlineKeyboardButton(text="ترافیک (گیگ)", callback_data=f"plan_edit_field:{plan_id}:traffic_gb")],
            [InlineKeyboardButton(text="قیمت", callback_data=f"plan_edit_field:{plan_id}:price")],
            [InlineKeyboardButton(text="قیمت عمده‌فروشی", callback_data=f"plan_edit_field:{plan_id}:wholesale_price")],
            [InlineKeyboardButton(text=t.BTN_BACK, callback_data="plan_edit_cancel")],
        ]
    )


def admin_wholesalers_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ افزودن عمده‌فروش", callback_data="wholesaler_add")],
            [InlineKeyboardButton(text="➖ حذف عمده‌فروش", callback_data="wholesaler_remove")],
            [InlineKeyboardButton(text="↩ بازگشت", callback_data="wholesaler_back")],
        ]
    )


def yes_no_inline(prefix: str, item_id: int | str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t.BTN_CONFIRM, callback_data=f"{prefix}_yes:{item_id}"),
                InlineKeyboardButton(text=t.BTN_CANCEL, callback_data=f"{prefix}_no:{item_id}"),
            ]
        ]
    )


def customer_manage_keyboard(telegram_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📋 مشاهده سرویس‌ها", callback_data=f"cust_svc_list:{telegram_id}")],
            [InlineKeyboardButton(text="➕ افزودن سرویس", callback_data=f"cust_svc_add:{telegram_id}")],
            [InlineKeyboardButton(text="💳 تغییر موجودی کیف پول", callback_data=f"cust_wallet:{telegram_id}")],
            [InlineKeyboardButton(text="↩ بازگشت", callback_data="cust_back")],
        ]
    )


def customer_services_keyboard(telegram_id: int, services: list) -> InlineKeyboardMarkup:
    rows = []
    for s in services:
        status_icon = "✅" if s.status == "active" else "🚫"
        rows.append([InlineKeyboardButton(text=f"{status_icon} سرویس #{s.id} — {s.panel_username}", callback_data=f"cust_svc_view:{telegram_id}:{s.id}")])
    rows.append([InlineKeyboardButton(text="↩ بازگشت", callback_data=f"cust_back_to:{telegram_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def customer_service_actions_keyboard(telegram_id: int, service_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚫 غیرفعال کردن", callback_data=f"cust_svc_disable:{telegram_id}:{service_id}")],
            [InlineKeyboardButton(text="🗑 حذف از پنل", callback_data=f"cust_svc_delete:{telegram_id}:{service_id}")],
            [InlineKeyboardButton(text="↩ بازگشت", callback_data=f"cust_svc_list:{telegram_id}")],
        ]
    )


def connect_platform_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t.CONNECT_PLATFORM_IOS), KeyboardButton(text=t.CONNECT_PLATFORM_ANDROID)],
            [KeyboardButton(text=t.BTN_BACK)],
        ],
        resize_keyboard=True,
    )


CONNECT_APPS = {
    "ios": [("v2box", True), ("NapsternetV", False)],
    "android": [("v2rayNG", True), ("v2box", True), ("NapsternetV", False) ],
}


def connect_apps_keyboard(platform: str) -> ReplyKeyboardMarkup:
    rows = []
    for name, recommended in CONNECT_APPS.get(platform, []):
        label = f"{name} ⭐️ پیشنهاد ما" if recommended else name
        rows.append([KeyboardButton(text=label)])
    rows.append([KeyboardButton(text=t.BTN_BACK)])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)
