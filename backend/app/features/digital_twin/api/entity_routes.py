"""Entity API routes - CRUD, search, state management, and bulk operations."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.features.digital_twin.api.deps import get_entity_service, get_event_service
from app.features.digital_twin.api.route_utils import unwrap_or_raise
from app.features.digital_twin.dto.entity_requests import (
    BulkUpdateStateRequest,
    CreateEntityRequest,
    UpdateEntityRequest,
    UpdateEntityStateRequest,
)
from app.features.digital_twin.dto.entity_responses import (
    BulkUpdateResponse,
    EntityListResponse,
    EntityResponse,
    PaginatedEntityResponse,
)
from app.features.digital_twin.services.entity_service import EntityService
from app.features.digital_twin.services.event_service import EventService

router = APIRouter(prefix="/entities", tags=["Entities"])


@router.post(
    "/", response_model=EntityResponse, status_code=201,
    summary="Create a new entity in the digital twin",
)
async def create_entity(
    body: CreateEntityRequest,
    entity_service: Annotated[EntityService, Depends(get_entity_service)],
) -> EntityResponse:
    result = await entity_service.create_entity(body)
    return unwrap_or_raise(result)  # type: ignore[return-value]


@router.get(
    "/search", response_model=PaginatedEntityResponse,
    summary="Search entities with filters and pagination",
)
async def search_entities(
    entity_type: str | None = Query(None),
    operational_status: str | None = Query(None),
    current_health: str | None = Query(None),
    zone_id: str | None = Query(None),
    venue_id: str | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    entity_service: Annotated[EntityService, Depends(get_entity_service)],
) -> PaginatedEntityResponse:
    from app.features.digital_twin.models.entity_state import EntityHealth, OperationalStatus
    from app.features.digital_twin.models.entity_type import EntityType

    result = await entity_service.search_entities({
        "entity_type": EntityType(entity_type) if entity_type else None,
        "operational_status": OperationalStatus(operational_status) if operational_status else None,
        "current_health": EntityHealth(current_health) if current_health else None,
        "zone_id": zone_id, "venue_id": venue_id,
        "search": search, "page": page, "page_size": page_size,
    })
    return unwrap_or_raise(result)  # type: ignore[return-value]


@router.get(
    "/{entity_id}", response_model=EntityResponse,
    summary="Get a single entity by ID",
)
async def get_entity(
    entity_id: str,
    entity_service: Annotated[EntityService, Depends(get_entity_service)],
) -> EntityResponse:
    result = await entity_service.get_entity(entity_id)
    return unwrap_or_raise(result)  # type: ignore[return-value]


@router.put(
    "/{entity_id}", response_model=EntityResponse,
    summary="Update entity properties",
)
async def update_entity(
    entity_id: str,
    body: UpdateEntityRequest,
    entity_service: Annotated[EntityService, Depends(get_entity_service)],
) -> EntityResponse:
    result = await entity_service.update_entity(entity_id, body)
    return unwrap_or_raise(result)  # type: ignore[return-value]


@router.patch(
    "/{entity_id}/state",
    summary="Update real-time state of an entity",
)
async def update_entity_state(
    entity_id: str,
    body: UpdateEntityStateRequest,
    entity_service: Annotated[EntityService, Depends(get_entity_service)],
) -> dict:
    result = await entity_service.update_state(entity_id, body)
    unwrap_or_raise(result)
    return {"message": "State updated successfully"}


@router.post(
    "/bulk/state", response_model=BulkUpdateResponse,
    summary="Bulk update state for multiple entities",
)
async def bulk_update_state(
    body: BulkUpdateStateRequest,
    entity_service: Annotated[EntityService, Depends(get_entity_service)],
) -> BulkUpdateResponse:
    result = await entity_service.bulk_update_state(body)
    return unwrap_or_raise(result)  # type: ignore[return-value]


@router.get(
    "/{entity_id}/events", response_model=EntityListResponse,
    summary="Get event history for an entity",
)
async def get_entity_events(
    entity_id: str,
    event_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    event_service: Annotated[EventService, Depends(get_event_service)],
) -> EntityListResponse:
    result = await event_service.get_entity_events(
        entity_id, event_type=event_type, page=page, page_size=page_size,
    )
    return result.value


@router.delete(
    "/{entity_id}",
    summary="Soft-delete an entity",
)
async def delete_entity(
    entity_id: str,
    entity_service: Annotated[EntityService, Depends(get_entity_service)],
) -> dict:
    result = await entity_service.delete_entity(entity_id)
    unwrap_or_raise(result)
    return {"message": "Entity deleted successfully"}
