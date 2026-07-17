"""Entity repository - data access layer with spatial query support."""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import Float, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.digital_twin.models.entity import Entity
from app.features.digital_twin.models.entity_state import (
    EntityHealth,
    OperationalStatus,
)
from app.features.digital_twin.models.entity_type import EntityType
from app.shared.result import Failure, Result, Success


class EntityRepository:
    """Handles all database operations for the Entity model.

    Supports spatial queries, paginated search, bulk updates,
    and hierarchical entity lookups.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, entity_id: uuid.UUID) -> Result[Entity | None]:
        """Fetch an entity by ID, excluding soft-deleted."""
        stmt = select(Entity).where(
            Entity.id == entity_id, Entity.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return Success(result.scalar_one_or_none())

    async def get_by_ids(self, entity_ids: list[uuid.UUID]) -> Result[Sequence[Entity]]:
        """Fetch multiple entities by their IDs."""
        stmt = select(Entity).where(
            Entity.id.in_(entity_ids), Entity.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return Success(result.scalars().all())

    async def create(self, entity: Entity) -> Result[Entity]:
        """Persist a new entity."""
        self._session.add(entity)
        await self._session.flush()
        return Success(entity)

    async def update(self, entity: Entity) -> Result[Entity]:
        """Update an existing entity. Flushes without committing."""
        await self._session.flush()
        return Success(entity)

    async def update_state(
        self,
        entity_id: uuid.UUID,
        *,
        operational_status: OperationalStatus | None = None,
        current_health: EntityHealth | None = None,
        current_capacity: int | None = None,
        current_state: dict | None = None,
    ) -> Result[None]:
        """Atomically update entity real-time state fields."""
        values: dict = {}
        if operational_status is not None:
            values["operational_status"] = operational_status
        if current_health is not None:
            values["current_health"] = current_health
        if current_capacity is not None:
            values["current_capacity"] = current_capacity
        if current_state is not None:
            values["current_state"] = current_state

        if not values:
            return Success(None)

        stmt = update(Entity).where(Entity.id == entity_id).values(**values)
        await self._session.execute(stmt)
        return Success(None)

    async def search(
        self,
        *,
        entity_type: EntityType | None = None,
        operational_status: OperationalStatus | None = None,
        current_health: EntityHealth | None = None,
        zone_id: uuid.UUID | None = None,
        venue_id: uuid.UUID | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Result[tuple[list[Entity], int]]:
        """Search entities with multiple filters and pagination."""
        base_query = select(Entity).where(Entity.deleted_at.is_(None))

        if entity_type is not None:
            base_query = base_query.where(Entity.entity_type == entity_type)
        if operational_status is not None:
            base_query = base_query.where(Entity.operational_status == operational_status)
        if current_health is not None:
            base_query = base_query.where(Entity.current_health == current_health)
        if zone_id is not None:
            base_query = base_query.where(Entity.zone_id == zone_id)
        if venue_id is not None:
            base_query = base_query.where(Entity.venue_id == venue_id)
        if search:
            # Escape SQL LIKE wildcards to prevent pattern injection
            escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            pattern = f"%{escaped}%"
            base_query = base_query.where(Entity.name.ilike(pattern, escape="\\"))

        count_stmt = select(func.count()).select_from(base_query.subquery())
        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar_one()

        paginated = base_query.order_by(Entity.created_at.desc()).offset(
            (page - 1) * page_size,
        ).limit(page_size)

        result = await self._session.execute(paginated)
        entities = list(result.scalars().all())
        return Success((entities, total))

    async def find_nearby(
        self,
        lat: float,
        lon: float,
        radius_meters: float,
        entity_type: EntityType | None = None,
        limit: int = 20,
    ) -> Result[list[tuple[Entity, float]]]:
        """Find entities within a radius using the Haversine formula.

        Returns tuples of (entity, distance_meters) sorted by distance.
        """
        lat_rad = func.radians(lat)
        lon_rad = func.radians(lon)
        dlat = func.radians(Entity.coordinates_lat) - lat_rad
        dlon = func.radians(Entity.coordinates_lon) - lon_rad
        a = func.power(func.sin(dlat / 2), 2) + func.cos(lat_rad) * func.cos(
            func.radians(Entity.coordinates_lat),
        ) * func.power(func.sin(dlon / 2), 2)
        distance = func.cast(6371000 * 2 * func.asin(func.sqrt(a)), type_=Float)

        stmt = (
            select(Entity, distance.label("dist"))
            .where(Entity.deleted_at.is_(None), distance <= radius_meters)
        )
        if entity_type is not None:
            stmt = stmt.where(Entity.entity_type == entity_type)

        stmt = stmt.order_by(distance).limit(limit)
        result = await self._session.execute(stmt)
        rows = result.all()
        return Success([(row[0], float(row[1])) for row in rows])

    async def find_in_bounds(
        self,
        lat_min: float,
        lat_max: float,
        lon_min: float,
        lon_max: float,
        entity_type: EntityType | None = None,
        limit: int = 100,
    ) -> Result[list[Entity]]:
        """Find entities within a bounding box for efficient spatial filtering."""
        stmt = (
            select(Entity)
            .where(
                Entity.deleted_at.is_(None),
                Entity.coordinates_lat >= lat_min,
                Entity.coordinates_lat <= lat_max,
                Entity.coordinates_lon >= lon_min,
                Entity.coordinates_lon <= lon_max,
            )
        )
        if entity_type is not None:
            stmt = stmt.where(Entity.entity_type == entity_type)

        stmt = stmt.limit(limit)
        result = await self._session.execute(stmt)
        return Success(list(result.scalars().all()))

    async def batch_update_state(
        self,
        entity_ids: list[uuid.UUID],
        *,
        operational_status: OperationalStatus | None = None,
        current_health: EntityHealth | None = None,
        current_capacity: int | None = None,
        current_state: dict | None = None,
    ) -> Result[int]:
        """Batch-update state for multiple entities in a single query."""
        values: dict = {}
        if operational_status is not None:
            values["operational_status"] = operational_status
        if current_health is not None:
            values["current_health"] = current_health
        if current_capacity is not None:
            values["current_capacity"] = current_capacity
        if current_state is not None:
            values["current_state"] = current_state

        if not values or not entity_ids:
            return Success(0)

        stmt = update(Entity).where(Entity.id.in_(entity_ids)).values(**values)
        result = await self._session.execute(stmt)
        return Success(result.rowcount)

    async def delete(self, entity_id: uuid.UUID) -> Result[None]:
        """Soft-delete an entity."""
        stmt = update(Entity).where(Entity.id == entity_id).values(
            deleted_at=func.now(),
        )
        await self._session.execute(stmt)
        return Success(None)

    async def count_by_venue(self, venue_id: uuid.UUID) -> Result[int]:
        """Count all non-deleted entities for a venue."""
        stmt = select(func.count()).where(
            Entity.venue_id == venue_id, Entity.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return Success(result.scalar_one())
