"""Aggregation repository — data access for windowed event aggregations."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.event_streaming.models.aggregation import EventAggregation
from app.shared.result import Result, Success


class AggregationRepository:
    """Handles all database operations for the EventAggregation model."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(self, aggregation: EventAggregation) -> Result[EventAggregation]:
        """Insert or update a windowed aggregation."""
        stmt = select(EventAggregation).where(
            EventAggregation.venue_id == aggregation.venue_id,
            EventAggregation.zone_id == aggregation.zone_id,
            EventAggregation.window_type == aggregation.window_type,
            EventAggregation.window_start == aggregation.window_start,
        )
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing is not None:
            existing.event_count = aggregation.event_count
            existing.events_by_category = aggregation.events_by_category
            existing.events_by_severity = aggregation.events_by_severity
            existing.peak_crowd_density = aggregation.peak_crowd_density
            existing.avg_crowd_density = aggregation.avg_crowd_density
            existing.avg_response_time_ms = aggregation.avg_response_time_ms
            existing.max_response_time_ms = aggregation.max_response_time_ms
            existing.anomalies_detected = aggregation.anomalies_detected
            existing.alerts_triggered = aggregation.alerts_triggered
            existing.summary = aggregation.summary
            await self._session.flush()
            return Success(existing)

        self._session.add(aggregation)
        await self._session.flush()
        return Success(aggregation)

    async def get_latest(
        self,
        venue_id: uuid.UUID,
        window_type: str,
        zone_id: uuid.UUID | None = None,
    ) -> Result[EventAggregation | None]:
        """Get the most recent aggregation for a venue/window/zone."""
        stmt = (
            select(EventAggregation)
            .where(
                EventAggregation.venue_id == venue_id,
                EventAggregation.window_type == window_type,
            )
        )
        if zone_id is not None:
            stmt = stmt.where(EventAggregation.zone_id == zone_id)
        else:
            stmt = stmt.where(EventAggregation.zone_id.is_(None))

        stmt = stmt.order_by(EventAggregation.window_start.desc()).limit(1)
        result = await self._session.execute(stmt)
        return Success(result.scalar_one_or_none())

    async def get_time_range(
        self,
        venue_id: uuid.UUID,
        window_type: str,
        from_time: str,
        to_time: str,
    ) -> Result[list[EventAggregation]]:
        """Fetch aggregations within a time range for trend analysis."""
        stmt = (
            select(EventAggregation)
            .where(
                EventAggregation.venue_id == venue_id,
                EventAggregation.window_type == window_type,
                EventAggregation.window_start >= from_time,
                EventAggregation.window_end <= to_time,
            )
            .order_by(EventAggregation.window_start.asc())
        )
        result = await self._session.execute(stmt)
        return Success(list(result.scalars().all()))
