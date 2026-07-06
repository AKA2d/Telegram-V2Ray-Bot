from sqlalchemy import select

from .db import async_session
from .models import Card
from .settings_repo import get_setting, set_setting

ROUND_ROBIN_SETTING_KEY = "round_robin_last_card_id"


async def list_cards() -> list[Card]:
    async with async_session() as session:
        result = await session.execute(select(Card).order_by(Card.display_order))
        return list(result.scalars().all())


async def list_active_cards() -> list[Card]:
    async with async_session() as session:
        result = await session.execute(select(Card).where(Card.is_active == True).order_by(Card.display_order))  # noqa: E712
        return list(result.scalars().all())


async def get_round_robin_card() -> Card | None:
    """Pick the next card in rotation among active cards, persisting the cursor."""
    cards = await list_active_cards()
    if not cards:
        return None
    ids = [c.id for c in cards]
    last_id_raw = await get_setting(ROUND_ROBIN_SETTING_KEY)
    idx = 0
    if last_id_raw and last_id_raw != "0":
        try:
            idx = (ids.index(int(last_id_raw)) + 1) % len(ids)
        except ValueError:
            idx = 0
    chosen = cards[idx]
    await set_setting(ROUND_ROBIN_SETTING_KEY, str(chosen.id))
    return chosen


async def get_next_card(current_card_id: int | None) -> Card | None:
    """Used by the 'next card' button when the current card turns out to be limited."""
    cards = await list_active_cards()
    if not cards:
        return None
    if current_card_id is None:
        return cards[0]
    ids = [c.id for c in cards]
    try:
        idx = ids.index(current_card_id)
    except ValueError:
        return cards[0]
    if len(cards) <= 1:
        return None
    return cards[(idx + 1) % len(cards)]


async def add_card(card_number: str, holder_name: str | None) -> Card:
    async with async_session() as session:
        result = await session.execute(select(Card))
        count = len(result.scalars().all())
        card = Card(card_number=card_number, holder_name=holder_name, is_active=True, display_order=count)
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


async def toggle_card_active(card_id: int) -> None:
    async with async_session() as session:
        card = await session.get(Card, card_id)
        if card:
            card.is_active = not card.is_active
            await session.commit()
