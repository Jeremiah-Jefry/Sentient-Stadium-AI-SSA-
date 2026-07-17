"""Sensor registry repository — data access for sensor management."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.event_streaming.models.sensor import SensorRegistry
from app.shared.result import Result, Success


class SensorRepository:
    """Handles all database operations for the SensorRegistry model."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, sensor: SensorRegistry) -> Result[SensorRegistry]:
        """Register a new sensor."""
        self._session.add(sensor)
        await self._session.flush()
        return Success(sensor)

    async def get_by_id(self, sensor_id: uuid.UUID) -> Result[SensorRegistry | None]:
        """Fetch a sensor by ID, excluding soft-deleted."""
        stmt = select(SensorRegistry).where(
            SensorRegistry.id == sensor_id,
            SensorRegistry.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return Success(result.scalar_one_or_none())

    async def get_by_ids(self, sensor_ids: list[uuid.UUID]) -> Result[list[SensorRegistry]]:
        """Fetch multiple sensors by their IDs."""
        stmt = select(SensorRegistry).where(
            SensorRegistry.id.in_(sensor_ids),
            SensorRegistry.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return Success(list(result.scalars().all()))

    async def update(self, sensor: SensorRegistry) -> Result[SensorRegistry]:
        """Update sensor metadata. Flushes without committing."""
        await self._session.flush()
        return Success(sensor)

    async def search(
        self,
        *,
        venue_id: uuid.UUID | None = None,
        zone_id: uuid.UUID | None = None,
        sensor_type: str | None = None,
        is_active: bool | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Result[tuple[list[SensorRegistry], int]]:
        """Search sensors with filters and pagination."""
        base_query = select(SensorRegistry).where(SensorRegistry.deleted_at.is_(None))

        if venue_id is not None:
            base_query = base_query.where(SensorRegistry.venue_id == venue_id)
        if zone_id is not None:
            base_query = base_query.where(SensorRegistry.zone_id == zone_id)
        if sensor_type is not None:
            base_query = base_query.where(SensorRegistry.sensor_type == sensor_type)
        if is_active is not None:
            base_query = base_query.where(SensorRegistry.is_active == is_active)

        count_stmt = select(func.count()).select_from(base_query.subquery())
        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar_one()

        paginated = base_query.order_by(SensorRegistry.created_at.desc()).offset(
            (page - 1) * page_size,
        ).limit(page_size)

        result = await self._session.execute(paginated)
        sensors = list(result.scalars().all())
        return Success((sensors, total))

    async def get_active_by_venue(self, venue_id: uuid.UUID) -> Result[list[SensorRegistry]]:
        """Fetch all active sensors for a venue."""
        stmt = (
            select(SensorRegistry)
            .where(
                SensorRegistry.venue_id == venue_id,
                SensorRegistry.is_active.is_(True),
                SensorRegistry.deleted_at.is_(None),
            )
            .order_by(SensorRegistry.sensor_type)
        )
        result = await self._session.execute(stmt)
        return Success(list(result.scalars().all()))

    async def count_by_venue(self, venue_id: uuid.UUID) -> Result[dict[str, int]]:
        """Count sensors grouped by active status for a venue."""
        stmt = (
            select(
                SensorRegistry.is_active,
                func.count(),
            )
            .where(
                SensorRegistry.venue_id == venue_id,
                SensorRegistry.deleted_at.is_(None),
            )
            .group_by(SensorRegistry.is_active)
        )
        result = await self._session.execute(stmt)
        rows = result.all()
        counts = {"active": 0, "inactive": 0}
        for is_active, count in rows:
            key = "active" if is_active else "inactive"
            counts[key] = count
        return Success(counts)

    async def soft_delete(self, sensor_id: uuid.UUID) -> Result[None]:
        """Soft-delete a sensor."""
        stmt = update(SensorRegistry).where(SensorRegistry.id == sensor_id).values(
            deleted_at=func.now(),
        )
        await self._session.execute(stmt)
        return Success(None)
