"""Zone repository - hierarchy queries and spatial lookups for zones."""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.digital_twin.models.zone import Zone
from app.shared.result import Result, Success


class ZoneRepository:
    """Handles all database operations for the Zone model.

    Supports hierarchical tree queries, ancestry lookups,
    and zone-based entity aggregation.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, zone_id: uuid.UUID) -> Result[Zone | None]:
        """Fetch a zone by ID, excluding soft-deleted."""
        stmt = select(Zone).where(Zone.id == zone_id, Zone.deleted_at.is_(None))
        result = await self._session.execute(stmt)
        return Success(result.scalar_one_or_none())

    async def get_children(self, parent_zone_id: uuid.UUID) -> Result[list[Zone]]:
        """Fetch direct child zones of a parent zone."""
        stmt = (
            select(Zone)
            .where(Zone.parent_zone_id == parent_zone_id, Zone.deleted_at.is_(None))
            .order_by(Zone.level, Zone.name)
        )
        result = await self._session.execute(stmt)
        return Success(list(result.scalars().all()))

    async def get_ancestors(self, zone_id: uuid.UUID) -> Result[list[Zone]]:
        """Walk up the tree to get all ancestor zones from root to parent.

        Uses recursive CTE to traverse the zone hierarchy.
        """
        recursive_cte = (
            select(Zone)
            .where(Zone.id == zone_id)
            .cte(name="zone_ancestors", recursive=True)
        )
        recursive_cte = recursive_cte.union_all(
            select(Zone).join(
                recursive_cte, Zone.id == recursive_cte.c.parent_zone_id,
            ),
        )
        stmt = (
            select(Zone)
            .from_statement(select(Zone).where(Zone.id.in_(select(recursive_cte.c.id))))
        )
        result = await self._session.execute(stmt)
        return Success(list(result.scalars().all()))

    async def get_descendants(self, zone_id: uuid.UUID) -> Result[list[Zone]]:
        """Fetch all descendant zones recursively using CTE."""
        recursive_cte = (
            select(Zone)
            .where(Zone.id == zone_id)
            .cte(name="zone_descendants", recursive=True)
        )
        recursive_cte = recursive_cte.union_all(
            select(Zone).where(Zone.parent_zone_id == recursive_cte.c.id),
        )
        stmt = select(Zone).where(Zone.id.in_(select(recursive_cte.c.id)))
        result = await self._session.execute(stmt)
        return Success(list(result.scalars().all()))

    async def get_root_zones(self, venue_id: uuid.UUID) -> Result[list[Zone]]:
        """Fetch top-level zones (no parent) for a venue."""
        stmt = (
            select(Zone)
            .where(
                Zone.venue_id == venue_id,
                Zone.parent_zone_id.is_(None),
                Zone.deleted_at.is_(None),
            )
            .order_by(Zone.name)
        )
        result = await self._session.execute(stmt)
        return Success(list(result.scalars().all()))

    async def create(self, zone: Zone) -> Result[Zone]:
        """Persist a new zone."""
        self._session.add(zone)
        await self._session.flush()
        return Success(zone)

    async def update(self, zone: Zone) -> Result[Zone]:
        """Update an existing zone."""
        await self._session.flush()
        return Success(zone)

    async def delete(self, zone_id: uuid.UUID) -> Result[None]:
        """Soft-delete a zone."""
        stmt = update(Zone).where(Zone.id == zone_id).values(deleted_at=func.now())
        await self._session.execute(stmt)
        return Success(None)

    async def would_create_cycle(
        self, zone_id: uuid.UUID, new_parent_id: uuid.UUID,
    ) -> Result[bool]:
        """Check if setting new_parent_id as parent would create a cycle."""
        if zone_id == new_parent_id:
            return Success(True)

        descendants = await self.get_descendants(zone_id)
        descendant_ids = {z.id for z in descendants.value}
        return Success(new_parent_id in descendant_ids)

    async def list_by_venue(self, venue_id: uuid.UUID) -> Result[list[Zone]]:
        """List all zones for a venue ordered by level and name."""
        stmt = (
            select(Zone)
            .where(Zone.venue_id == venue_id, Zone.deleted_at.is_(None))
            .order_by(Zone.level, Zone.name)
        )
        result = await self._session.execute(stmt)
        return Success(list(result.scalars().all()))
