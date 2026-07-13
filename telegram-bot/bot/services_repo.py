from sqlalchemy import select, or_

from .db import async_session
from .models import Service


async def create_service(**kwargs) -> Service:
    async with async_session() as session:
        service = Service(**kwargs)
        session.add(service)
        await session.commit()
        await session.refresh(service)
        return service


async def get_service(service_id: int) -> Service | None:
    async with async_session() as session:
        return await session.get(Service, service_id)


async def list_user_services(telegram_id: int) -> list[Service]:
    async with async_session() as session:
        result = await session.execute(
            select(Service).where(Service.owner_telegram_id == telegram_id).order_by(Service.created_at.desc())
        )
        return list(result.scalars().all())


async def find_service_by_link_or_uuid(query: str) -> Service | None:
    async with async_session() as session:
        result = await session.execute(
            select(Service).where(
                or_(Service.subscription_link == query, Service.panel_uuid == query, Service.panel_username == query)
            )
        )
        return result.scalars().first()


async def update_service(service_id: int, **kwargs) -> Service | None:
    async with async_session() as session:
        service = await session.get(Service, service_id)
        if not service:
            return None
        for key, value in kwargs.items():
            setattr(service, key, value)
        await session.commit()
        await session.refresh(service)
        return service


async def count_user_services(telegram_id: int) -> tuple[int, int]:
    async with async_session() as session:
        result = await session.execute(select(Service).where(Service.owner_telegram_id == telegram_id))
        services = list(result.scalars().all())
        total = len(services)
        active = len([s for s in services if s.status == "active"])
        return total, active


async def count_all_services() -> int:
    async with async_session() as session:
        result = await session.execute(select(Service))
        return len(result.scalars().all())
