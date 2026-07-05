from sqlalchemy import select

from .db import async_session
from .models import User


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
