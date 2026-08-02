from decimal import Decimal

from sqlalchemy import select

from .db import async_session
from .models import User, WalletAuditLog


async def get_or_create_user(telegram_id: int, username: str | None, first_name: str | None) -> User:
    async with async_session() as session:
        user = await session.get(User, telegram_id)
        if user:
            changed = False
            if user.username != username:
                user.username = username
                changed = True
            if user.first_name != first_name:
                user.first_name = first_name
                changed = True
            if changed:
                await session.commit()
            return user
        user = User(telegram_id=telegram_id, username=username, first_name=first_name)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def find_user(query: str) -> User | None:
    async with async_session() as session:
        if query.isdigit():
            user = await session.get(User, int(query))
            if user:
                return user
        result = await session.execute(select(User).where(User.username == query.lstrip("@")))
        return result.scalars().first()


async def all_user_ids() -> list[int]:
    async with async_session() as session:
        result = await session.execute(select(User.telegram_id))
        return [row[0] for row in result.all()]


async def debit_wallet(telegram_id: int, amount: int, reason: str) -> Decimal | None:
    """Atomically debit a wallet, returning the new balance on success."""
    if amount <= 0:
        raise ValueError("Wallet debit amount must be positive")

    async with async_session() as session:
        async with session.begin():
            user = await session.get(User, telegram_id, with_for_update=True)
            debit = Decimal(amount)
            if user is None or user.wallet_balance < debit:
                return None
            old_balance = user.wallet_balance
            user.wallet_balance = old_balance - debit
            session.add(
                WalletAuditLog(
                    telegram_id=telegram_id,
                    old_balance=old_balance,
                    new_balance=user.wallet_balance,
                    reason=reason,
                )
            )
            return user.wallet_balance


async def credit_wallet(telegram_id: int, amount: int, reason: str) -> Decimal | None:
    """Atomically credit a wallet; used to compensate a failed payment flow."""
    if amount <= 0:
        raise ValueError("Wallet credit amount must be positive")

    async with async_session() as session:
        async with session.begin():
            user = await session.get(User, telegram_id, with_for_update=True)
            if user is None:
                return None
            old_balance = user.wallet_balance
            user.wallet_balance = old_balance + Decimal(amount)
            session.add(
                WalletAuditLog(
                    telegram_id=telegram_id,
                    old_balance=old_balance,
                    new_balance=user.wallet_balance,
                    reason=reason,
                )
            )
            return user.wallet_balance
