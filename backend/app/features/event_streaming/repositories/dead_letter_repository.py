"""Dead letter repository — data access for failed events."""

from __future__ import annotations

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.event_streaming.models.dead_letter import DeadLetterEvent
from app.shared.result import Result, Success


class DeadLetterRepository:
    """Handles all database operations for the DeadLetterEvent model."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(self, event: DeadLetterEvent) -> Result[DeadLetterEvent]:
        """Store a failed event in the dead letter queue."""
        self._session.add(event)
        await self._session.flush()
        return Success(event)

    async def get_unresolved(
        self, page: int = 1, page_size: int = 50,
    ) -> Result[tuple[list[DeadLetterEvent], int]]:
        """Fetch unresolved dead letter events with pagination."""
        base_query = select(DeadLetterEvent).where(DeadLetterEvent.is_resolved.is_(False))

        count_stmt = select(func.count()).select_from(base_query.subquery())
        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar_one()

        paginated = base_query.order_by(DeadLetterEvent.created_at.desc()).offset(
            (page - 1) * page_size,
        ).limit(page_size)

        result = await self._session.execute(paginated)
        events = list(result.scalars().all())
        return Success((events, total))

    async def mark_resolved(
        self,
        event_id: str,
        resolved_by: str,
        notes: str | None = None,
    ) -> Result[None]:
        """Mark a dead letter event as resolved."""
        stmt = (
            update(DeadLetterEvent)
            .where(DeadLetterEvent.id == event_id)
            .values(
                is_resolved=True,
                resolved_by=resolved_by,
                resolution_notes=notes,
            )
        )
        await self._session.execute(stmt)
        return Success(None)

    async def count_unresolved(self) -> Result[int]:
        """Count unresolved dead letter events."""
        stmt = select(func.count()).where(DeadLetterEvent.is_resolved.is_(False))
        result = await self._session.execute(stmt)
        return Success(result.scalar_one())
