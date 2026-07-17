"""Event repository - append-only event log queries."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.digital_twin.models.entity import Entity
from app.features.digital_twin.models.entity_event import EntityEvent
from app.shared.result import Result, Success


class EventRepository:
    """Handles all database operations for the EntityEvent model.

    Events are append-only. No updates or deletes are permitted.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, event: EntityEvent) -> Result[EntityEvent]:
        """Append a new event to the log."""
        self._session.add(event)
        await self._session.flush()
        return Success(event)

    async def create_many(self, events: list[EntityEvent]) -> Result[list[EntityEvent]]:
        """Batch-insert multiple events."""
        self._session.add_all(events)
        await self._session.flush()
        return Success(events)

    async def get_by_entity(
        self,
        entity_id: uuid.UUID,
        event_type: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Result[tuple[list[EntityEvent], int]]:
        """Fetch events for a specific entity with optional type filter."""
        base_query = select(EntityEvent).where(EntityEvent.entity_id == entity_id)
        if event_type is not None:
            base_query = base_query.where(EntityEvent.event_type == event_type)

        count_stmt = select(func.count()).select_from(base_query.subquery())
        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar_one()

        paginated = base_query.order_by(EntityEvent.created_at.desc()).offset(
            (page - 1) * page_size,
        ).limit(page_size)

        result = await self._session.execute(paginated)
        events = list(result.scalars().all())
        return Success((events, total))

    async def get_recent(
        self, venue_id: uuid.UUID, limit: int = 50,
    ) -> Result[list[EntityEvent]]:
        """Fetch the most recent events across a venue via explicit JOIN."""
        stmt = (
            select(EntityEvent)
            .join(Entity, EntityEvent.entity_id == Entity.id)
            .where(Entity.venue_id == venue_id, Entity.deleted_at.is_(None))
            .order_by(EntityEvent.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return Success(list(result.scalars().all()))
