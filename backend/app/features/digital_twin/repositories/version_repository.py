"""Version repository - immutable state snapshot queries for audit and rollback."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.digital_twin.models.entity_version import EntityVersion
from app.shared.result import Result, Success


class VersionRepository:
    """Handles all database operations for the EntityVersion model.

    Versions are immutable snapshots. Each new version increments the version number.
    Supports timeline queries, diff tracking, and rollback target identification.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, version: EntityVersion) -> Result[EntityVersion]:
        """Persist a new version snapshot."""
        self._session.add(version)
        await self._session.flush()
        return Success(version)

    async def get_latest(self, entity_id: uuid.UUID) -> Result[EntityVersion | None]:
        """Fetch the most recent version for an entity."""
        stmt = (
            select(EntityVersion)
            .where(EntityVersion.entity_id == entity_id)
            .order_by(EntityVersion.version.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return Success(result.scalar_one_or_none())

    async def get_by_version(
        self, entity_id: uuid.UUID, version: int,
    ) -> Result[EntityVersion | None]:
        """Fetch a specific version snapshot."""
        stmt = select(EntityVersion).where(
            EntityVersion.entity_id == entity_id,
            EntityVersion.version == version,
        )
        result = await self._session.execute(stmt)
        return Success(result.scalar_one_or_none())

    async def get_timeline(
        self, entity_id: uuid.UUID, limit: int = 50,
    ) -> Result[list[EntityVersion]]:
        """Fetch version history for an entity, newest first."""
        stmt = (
            select(EntityVersion)
            .where(EntityVersion.entity_id == entity_id)
            .order_by(EntityVersion.version.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return Success(list(result.scalars().all()))

    async def get_next_version_number(self, entity_id: uuid.UUID) -> Result[int]:
        """Compute the next version number for an entity."""
        stmt = select(func.coalesce(func.max(EntityVersion.version), 0)).where(
            EntityVersion.entity_id == entity_id,
        )
        result = await self._session.execute(stmt)
        max_version = result.scalar_one()
        return Success(max_version + 1)
