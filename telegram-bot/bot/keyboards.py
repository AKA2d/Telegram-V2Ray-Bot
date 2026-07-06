from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

from . import texts as t


def main_menu(is_admin: bool = False) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text=t.MAIN_MENU_BUY), KeyboardButton(text=t.MAIN_MENU_MANAGE)],
        [KeyboardButton(text=t.MAIN_MENU_ACCOUNT), KeyboardButton(text=t.MAIN_MENU_TOPUP)],
        [KeyboardButton(text=t.MAIN_MENU_CONNECT)],
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
            [InlineKeyboardButton(text=t.BTN_INCREASE_USERS, callback_data=f"svc_increase:{service_id}")],
            [InlineKeyboardButton(text=t.BTN_EXTEND, callback_data=f"svc_extend:{service_id}")],
        ]
    )


def services_list_keyboard(services: list) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"#{s.id} — {s.status}", callback_data=f"svc_view:{s.id}")] for s in services
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_menu_keyboard() -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text=t.ADMIN_MENU_ORDERS), KeyboardButton(text=t.ADMIN_MENU_PLANS)],
        [KeyboardButton(text=t.ADMIN_MENU_CUSTOMERS), KeyboardButton(text=t.ADMIN_MENU_WALLET)],
        [KeyboardButton(text=t.ADMIN_MENU_BROADCAST), KeyboardButton(text=t.ADMIN_MENU_DIRECT)],
        [KeyboardButton(text=t.ADMIN_MENU_CARDS), KeyboardButton(text=t.ADMIN_MENU_TUNNEL)],
        [KeyboardButton(text=t.ADMIN_MENU_WHOLESALERS)],
        [KeyboardButton(text=t.BTN_BACK)],
    ]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def plans_list_keyboard(plans: list) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"{p.name} — {int(p.price)} تومان", callback_data=f"plan_select:plan:{p.id}")]
        for p in plans
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def plan_confirm_keyboard(plan_type: str, plan_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t.CONFIRM_YES, callback_data=f"plan_confirm:{plan_type}:{plan_id}")],
            [InlineKeyboardButton(text=t.CONFIRM_NO, callback_data="plan_cancel")],
        ]
    )


def admin_plans_keyboard(plans: list) -> InlineKeyboardMarkup:
    rows = []
    for p in plans:
        status = "✅" if p.is_active else "🚫"
        label = f"{status} {p.name} — {p.user_count} کاربر / {p.months} ماه / {p.traffic_gb} گیگ / {int(p.price)} تومان"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"plan_toggle:{p.id}")])
        rows.append([InlineKeyboardButton(text=f"🗑 حذف {p.name}", callback_data=f"plan_remove:{p.id}")])
    rows.append([InlineKeyboardButton(text="➕ افزودن پلن جدید", callback_data="plan_add")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_wholesalers_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ افزودن عمده‌فروش", callback_data="wholesaler_add")],
            [InlineKeyboardButton(text="➖ حذف عمده‌فروش", callback_data="wholesaler_remove")],
            [InlineKeyboardButton(text="➕ افزودن پلن عمده‌فروشی", callback_data="wholesale_plan_add")],
            [InlineKeyboardButton(text="📋 لیست پلن‌های عمده‌فروشی", callback_data="wholesale_plan_list")],
            [InlineKeyboardButton(text="🔁 اختصاص پلن", callback_data="wholesaler_assign")],
            [InlineKeyboardButton(text="❌ حذف تخصیص", callback_data="wholesaler_unassign")],
            [InlineKeyboardButton(text="↩ بازگشت", callback_data="wholesaler_back")],
        ]
    )


def admin_wholesale_plans_keyboard(plans: list) -> InlineKeyboardMarkup:
    rows = []
    for p in plans:
        status = "✅" if p.is_active else "🚫"
        label = f"{status} {p.name} — {p.user_count} کاربر / {p.months} ماه / {p.traffic_gb} گیگ / {int(p.price)} تومان"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"wholesale_plan_toggle:{p.id}")])
        rows.append([InlineKeyboardButton(text=f"🗑 حذف {p.name}", callback_data=f"wholesale_plan_remove:{p.id}")])
    rows.append([InlineKeyboardButton(text="➕ افزودن پلن جدید", callback_data="wholesale_plan_add")])
    rows.append([InlineKeyboardButton(text="↩ بازگشت", callback_data="wholesaler_back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def wholesale_plans_list_keyboard(plans: list) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"{p.name} — {int(p.price)} تومان", callback_data=f"plan_select:wholesale:{p.id}")]
        for p in plans
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def wholesaler_plan_action_keyboard(plans: list, wholesaler_id: int, action: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"{p.name} — {int(p.price)} تومان", callback_data=f"{action}:{wholesaler_id}:{p.id}")]
        for p in plans
    ]
    rows.append([InlineKeyboardButton(text=t.BTN_CANCEL, callback_data="wholesaler_back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def yes_no_inline(prefix: str, item_id: int | str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t.BTN_CONFIRM, callback_data=f"{prefix}_yes:{item_id}"),
                InlineKeyboardButton(text=t.BTN_CANCEL, callback_data=f"{prefix}_no:{item_id}"),
            ]
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
    "ios": [("HAPP", True), ("v2box", True), ("NapsternetV", False)],
    "android": [("v2rayNG", True), ("HAPP", True), ("v2box", True), ("NapsternetV", False) ],
}


def connect_apps_keyboard(platform: str) -> ReplyKeyboardMarkup:
    rows = []
    for name, recommended in CONNECT_APPS.get(platform, []):
        label = f"{name} ⭐️ پیشنهاد ما" if recommended else name
        rows.append([KeyboardButton(text=label)])
    rows.append([KeyboardButton(text=t.BTN_BACK)])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)
