from sqlalchemy import select

from .db import async_session
from .models import Card


async def list_cards() -> list[Card]:
    async with async_session() as session:
        result = await session.execute(select(Card).order_by(Card.display_order))
        return list(result.scalars().all())


async def get_active_card() -> Card | None:
    async with async_session() as session:
        result = await session.execute(select(Card).where(Card.is_active == True).order_by(Card.display_order))  # noqa: E712
        return result.scalars().first()


async def get_next_card(current_card_id: int | None) -> Card | None:
    cards = await list_cards()
    if not cards:
        return None
    if current_card_id is None:
        return cards[0]
    ids = [c.id for c in cards]
    try:
        idx = ids.index(current_card_id)
    except ValueError:
        return cards[0]
    if idx + 1 < len(cards):
        return cards[idx + 1]
    return None


async def add_card(card_number: str, holder_name: str | None) -> Card:
    async with async_session() as session:
        result = await session.execute(select(Card))
        count = len(result.scalars().all())
        card = Card(card_number=card_number, holder_name=holder_name, is_active=(count == 0), display_order=count)
        session.add(card)
        await session.commit()
        await session.refresh(card)
        return card


async def remove_card(card_id: int) -> None:
    async with async_session() as session:
        card = await session.get(Card, card_id)
        if card:
            await session.delete(card)
            await session.commit()


async def set_active_card(card_id: int) -> None:
    async with async_session() as session:
        result = await session.execute(select(Card))
        for card in result.scalars().all():
            card.is_active = card.id == card_id
        await session.commit()
