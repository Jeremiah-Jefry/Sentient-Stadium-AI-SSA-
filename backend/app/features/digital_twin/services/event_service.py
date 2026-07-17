"""Event service - event log queries and real-time event distribution."""

from __future__ import annotations

import uuid

from app.features.digital_twin.dto.entity_responses import EntityEventResponse, EntityListResponse
from app.features.digital_twin.models.entity_event import EntityEvent
from app.features.digital_twin.repositories.event_repository import EventRepository
from app.shared.result import Result, Success


class EventService:
    """Manages entity event log queries and real-time event broadcasting.

    Events are append-only. This service reads events for dashboards
    and AI agents that need entity state change history.
    """

    def __init__(self, event_repo: EventRepository) -> None:
        self._event_repo = event_repo

    async def get_entity_events(
        self, entity_id: str, event_type: str | None = None,
        page: int = 1, page_size: int = 50,
    ) -> Result[EntityListResponse]:
        """Fetch events for a specific entity."""
        result = await self._event_repo.get_by_entity(
            entity_id=uuid.UUID(entity_id),
            event_type=event_type, page=page, page_size=page_size,
        )
        if not isinstance(result, Success):
            return Success(EntityListResponse(events=[], total=0))

        events, total = result.value
        return Success(EntityListResponse(
            events=[self._to_response(e) for e in events], total=total,
        ))

    async def get_recent_events(
        self, venue_id: str, limit: int = 50,
    ) -> Result[EntityListResponse]:
        """Fetch recent events across a venue."""
        result = await self._event_repo.get_recent(
            venue_id=uuid.UUID(venue_id), limit=limit,
        )
        if not isinstance(result, Success):
            return Success(EntityListResponse(events=[], total=0))

        return Success(EntityListResponse(
            events=[self._to_response(e) for e in result.value],
            total=len(result.value),
        ))

    def _to_response(self, event: EntityEvent) -> EntityEventResponse:
        """Convert an event model to an API response."""
        return EntityEventResponse(
            id=str(event.id),
            entity_id=str(event.entity_id),
            event_type=event.event_type,
            event_data=event.event_data,
            source=event.source,
            created_at=event.created_at.isoformat() if event.created_at else "",
        )
