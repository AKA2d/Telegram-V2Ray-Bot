from aiogram import F, Router
from aiogram.types import Message

from .. import texts as t
from ..services_repo import count_user_services
from ..users_repo import get_or_create_user

router = Router(name="account_info")


@router.message(F.text == t.MAIN_MENU_ACCOUNT)
async def account_info(message: Message):
    user = await get_or_create_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    total, active = await count_user_services(message.from_user.id)
    await message.answer(
        t.ACCOUNT_INFO.format(
            total_services=total,
            active_services=active,
            wallet_balance=int(user.wallet_balance),
        )
    )
