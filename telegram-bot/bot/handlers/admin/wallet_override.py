from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from ... import texts as t
from ...db import async_session
from ...keyboards import admin_menu_keyboard, cancel_keyboard, confirm_keyboard
from ...models import User, WalletAuditLog
from ...states import AdminWalletOverride
from ...users_repo import find_user
from .base import AdminOnlyMiddleware

router = Router(name="admin_wallet")
router.message.middleware(AdminOnlyMiddleware())


@router.message(F.text == t.ADMIN_MENU_WALLET)
async def start_wallet_override(message: Message, state: FSMContext):
    await state.set_state(AdminWalletOverride.target)
    await message.answer(t.ASK_CUSTOMER_QUERY, reply_markup=cancel_keyboard())


@router.message(AdminWalletOverride.target)
async def find_target(message: Message, state: FSMContext):
    user = await find_user(message.text.strip())
    if not user:
        await message.answer(t.CUSTOMER_NOT_FOUND, reply_markup=admin_menu_keyboard())
        await state.clear()
        return
    await state.update_data(target_telegram_id=user.telegram_id, old_balance=int(user.wallet_balance))
    await state.set_state(AdminWalletOverride.new_balance)
    await message.answer(t.ASK_WALLET_NEW_BALANCE, reply_markup=cancel_keyboard())


@router.message(AdminWalletOverride.new_balance)
async def set_new_balance(message: Message, state: FSMContext):
    try:
        new_balance = int(message.text.strip())
    except ValueError:
        await message.answer(t.INVALID_NUMBER)
        return
    if new_balance < 0:
        await message.answer(t.WALLET_NEGATIVE_ERROR)
        return

    data = await state.get_data()
    await state.update_data(new_balance=new_balance)
    await state.set_state(AdminWalletOverride.confirm)
    from ...keyboards import yes_no_inline

    await message.answer(
        t.CONFIRM_WALLET_CHANGE.format(
            telegram_id=data["target_telegram_id"], old=data["old_balance"], new=new_balance
        ),
        reply_markup=confirm_keyboard(),
    )


@router.message(AdminWalletOverride.confirm, F.text == t.BTN_CONFIRM)
async def apply_wallet_change(message: Message, state: FSMContext):
    data = await state.get_data()
    async with async_session() as session:
        user = await session.get(User, data["target_telegram_id"])
        if not user:
            await message.answer(t.CUSTOMER_NOT_FOUND, reply_markup=admin_menu_keyboard())
            await state.clear()
            return
        old_balance = user.wallet_balance
        new_balance = data["new_balance"]
        if new_balance < 0:
            await message.answer(t.WALLET_NEGATIVE_ERROR, reply_markup=admin_menu_keyboard())
            await state.clear()
            return
        user.wallet_balance = new_balance
        session.add(
            WalletAuditLog(
                telegram_id=user.telegram_id,
                old_balance=old_balance,
                new_balance=new_balance,
                reason="admin manual override",
            )
        )
        await session.commit()

    await message.answer(t.WALLET_CHANGE_DONE, reply_markup=admin_menu_keyboard())
    await state.clear()


@router.message(AdminWalletOverride.confirm, F.text == t.BTN_CANCEL)
async def cancel_wallet_change(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(t.CANCELLED, reply_markup=admin_menu_keyboard())
