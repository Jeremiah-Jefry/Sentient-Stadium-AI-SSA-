"""Venue repository - data access for top-level venue entities."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.digital_twin.models.venue import Venue
from app.shared.result import Result, Success


class VenueRepository:
    """Handles all database operations for the Venue model."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, venue_id: uuid.UUID) -> Result[Venue | None]:
        """Fetch a venue by ID, excluding soft-deleted."""
        stmt = select(Venue).where(Venue.id == venue_id, Venue.deleted_at.is_(None))
        result = await self._session.execute(stmt)
        return Success(result.scalar_one_or_none())

    async def create(self, venue: Venue) -> Result[Venue]:
        """Persist a new venue."""
        self._session.add(venue)
        await self._session.flush()
        return Success(venue)

    async def update(self, venue: Venue) -> Result[Venue]:
        """Update an existing venue."""
        await self._session.flush()
        return Success(venue)

    async def delete(self, venue_id: uuid.UUID) -> Result[None]:
        """Soft-delete a venue."""
        stmt = update(Venue).where(Venue.id == venue_id).values(deleted_at=func.now())
        await self._session.execute(stmt)
        return Success(None)

    async def list_all(self) -> Result[list[Venue]]:
        """List all non-deleted venues."""
        stmt = select(Venue).where(Venue.deleted_at.is_(None)).order_by(Venue.name)
        result = await self._session.execute(stmt)
        return Success(list(result.scalars().all()))
