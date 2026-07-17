"""Consumer offset repository — data access for tracking processing progress."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.event_streaming.models.consumer_offset import ConsumerOffset
from app.shared.result import Result, Success


class ConsumerOffsetRepository:
    """Handles all database operations for the ConsumerOffset model."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_consumer_id(self, consumer_id: str) -> Result[ConsumerOffset | None]:
        """Fetch offset for a consumer."""
        stmt = select(ConsumerOffset).where(ConsumerOffset.consumer_id == consumer_id)
        result = await self._session.execute(stmt)
        return Success(result.scalar_one_or_none())

    async def upsert(self, offset: ConsumerOffset) -> Result[ConsumerOffset]:
        """Create or update a consumer offset."""
        existing = await self.get_by_consumer_id(offset.consumer_id)
        if isinstance(existing, Success) and existing.value is not None:
            existing.value.last_processed_event_id = offset.last_processed_event_id
            existing.value.last_processed_at = offset.last_processed_at
            existing.value.events_processed = offset.events_processed
            existing.value.events_failed = offset.events_failed
            existing.value.avg_processing_ms = offset.avg_processing_ms
            existing.value.status = offset.status
            await self._session.flush()
            return Success(existing.value)

        self._session.add(offset)
        await self._session.flush()
        return Success(offset)

    async def get_all(self) -> Result[list[ConsumerOffset]]:
        """Fetch all consumer offsets."""
        stmt = select(ConsumerOffset).order_by(ConsumerOffset.consumer_id)
        result = await self._session.execute(stmt)
        return Success(list(result.scalars().all()))

    async def reset_offset(
        self, consumer_id: str, to_event_id: str | None = None,
    ) -> Result[None]:
        """Reset a consumer's offset for replay."""
        existing = await self.get_by_consumer_id(consumer_id)
        if isinstance(existing, Success) and existing.value is not None:
            existing.value.last_processed_event_id = to_event_id
            existing.value.events_processed = 0
            existing.value.events_failed = 0
            await self._session.flush()
        return Success(None)
