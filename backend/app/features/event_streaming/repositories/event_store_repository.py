"""Event store repository — data access for the append-only event log."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.event_streaming.models.event import StoredEvent
from app.shared.result import Result, Success

SEVERITY_ORDERS = {
    "info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4, "emergency": 5,
}


class EventStoreRepository:
    """Handles all database operations for the StoredEvent model.

    Events are append-only: no UPDATE or DELETE operations are permitted.
    Supports time-range queries, entity/venue filtering, and pagination.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(self, event: StoredEvent) -> Result[StoredEvent]:
        """Append a new event to the store."""
        self._session.add(event)
        await self._session.flush()
        return Success(event)

    async def append_many(self, events: list[StoredEvent]) -> Result[list[StoredEvent]]:
        """Batch-insert multiple events atomically."""
        self._session.add_all(events)
        await self._session.flush()
        return Success(events)

    async def get_by_event_id(self, event_id: str) -> Result[StoredEvent | None]:
        """Fetch a single event by its unique event_id."""
        stmt = select(StoredEvent).where(StoredEvent.event_id == event_id)
        result = await self._session.execute(stmt)
        return Success(result.scalar_one_or_none())

    async def exists(self, event_id: str) -> Result[bool]:
        """Check if an event_id already exists (for deduplication)."""
        stmt = select(func.count()).where(StoredEvent.event_id == event_id)
        result = await self._session.execute(stmt)
        return Success(result.scalar_one() > 0)

    async def query_events(
        self,
        *,
        venue_id: uuid.UUID | None = None,
        entity_id: uuid.UUID | None = None,
        category: str | None = None,
        event_type: str | None = None,
        severity_min: str | None = None,
        since: str | None = None,
        until: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Result[tuple[list[StoredEvent], int]]:
        """Query events with multiple filters and pagination."""
        base_query = select(StoredEvent)

        if venue_id is not None:
            base_query = base_query.where(StoredEvent.venue_id == venue_id)
        if entity_id is not None:
            base_query = base_query.where(StoredEvent.entity_id == entity_id)
        if category is not None:
            base_query = base_query.where(StoredEvent.category == category)
        if event_type is not None:
            base_query = base_query.where(StoredEvent.event_type == event_type)
        if severity_min is not None:
            min_severity = SEVERITY_ORDERS.get(severity_min, 0)
            valid_severities = [
                s for s, o in SEVERITY_ORDERS.items() if o >= min_severity
            ]
            base_query = base_query.where(StoredEvent.severity.in_(valid_severities))
        if since is not None:
            base_query = base_query.where(StoredEvent.captured_at >= since)
        if until is not None:
            base_query = base_query.where(StoredEvent.captured_at <= until)

        count_stmt = select(func.count()).select_from(base_query.subquery())
        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar_one()

        paginated = base_query.order_by(StoredEvent.captured_at.desc()).offset(
            (page - 1) * page_size,
        ).limit(page_size)

        result = await self._session.execute(paginated)
        events = list(result.scalars().all())
        return Success((events, total))

    async def get_time_range(
        self,
        from_timestamp: str,
        to_timestamp: str,
        venue_id: uuid.UUID | None = None,
        category: str | None = None,
        batch_size: int = 500,
    ) -> Result[list[StoredEvent]]:
        """Fetch events in a time range for replay, ordered chronologically."""
        stmt = select(StoredEvent).where(
            StoredEvent.captured_at >= from_timestamp,
            StoredEvent.captured_at <= to_timestamp,
        )
        if venue_id is not None:
            stmt = stmt.where(StoredEvent.venue_id == venue_id)
        if category is not None:
            stmt = stmt.where(StoredEvent.category == category)

        stmt = stmt.order_by(StoredEvent.captured_at.asc()).limit(batch_size)
        result = await self._session.execute(stmt)
        return Success(list(result.scalars().all()))

    async def count_by_venue(self, venue_id: uuid.UUID) -> Result[int]:
        """Count all events for a venue."""
        stmt = select(func.count()).where(StoredEvent.venue_id == venue_id)
        result = await self._session.execute(stmt)
        return Success(result.scalar_one())

    async def count_by_category(self, venue_id: uuid.UUID) -> Result[dict[str, int]]:
        """Count events grouped by category for a venue."""
        stmt = (
            select(StoredEvent.category, func.count())
            .where(StoredEvent.venue_id == venue_id)
            .group_by(StoredEvent.category)
        )
        result = await self._session.execute(stmt)
        return Success(dict(result.all()))
