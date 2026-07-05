from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from ... import texts as t
from ...keyboards import cancel_keyboard, admin_menu_keyboard
from ...orders_repo import count_user_orders
from ...services_repo import count_user_services
from ...states import AdminCustomerLookup
from ...users_repo import find_user
from .base import AdminOnlyMiddleware

router = Router(name="admin_customers")
router.message.middleware(AdminOnlyMiddleware())


def _deep_link(telegram_id: int, username: str | None) -> str:
    if username:
        return f"https://t.me/{username}"
    return f"tg://user?id={telegram_id}"


@router.message(F.text == t.ADMIN_MENU_CUSTOMERS)
async def start_lookup(message: Message, state: FSMContext):
    await state.set_state(AdminCustomerLookup.query)
    await message.answer(t.ASK_CUSTOMER_QUERY, reply_markup=cancel_keyboard())


@router.message(AdminCustomerLookup.query)
async def do_lookup(message: Message, state: FSMContext):
    user = await find_user(message.text.strip())
    if not user:
        await message.answer(t.CUSTOMER_NOT_FOUND, reply_markup=admin_menu_keyboard())
        await state.clear()
        return

    total_services, _ = await count_user_services(user.telegram_id)
    order_count = await count_user_orders(user.telegram_id)

    await message.answer(
        t.CUSTOMER_PROFILE.format(
            telegram_id=user.telegram_id,
            username=user.username or "-",
            wallet_balance=int(user.wallet_balance),
            service_count=total_services,
            order_count=order_count,
            deep_link=_deep_link(user.telegram_id, user.username),
        ),
        reply_markup=admin_menu_keyboard(),
    )
    await state.clear()
