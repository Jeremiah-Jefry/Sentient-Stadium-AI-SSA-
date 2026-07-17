"""Entity service - lifecycle management and business logic for entities."""

from __future__ import annotations

import uuid

from app.features.digital_twin.dto.entity_requests import (
    BulkUpdateStateRequest,
    CreateEntityRequest,
    SearchEntityRequest,
    UpdateEntityRequest,
    UpdateEntityStateRequest,
)
from app.features.digital_twin.dto.entity_responses import PaginatedEntityResponse
from app.features.digital_twin.models.entity import Entity
from app.features.digital_twin.models.entity_event import EntityEvent
from app.features.digital_twin.models.entity_version import EntityVersion
from app.features.digital_twin.repositories.entity_repository import EntityRepository
from app.features.digital_twin.repositories.event_repository import EventRepository
from app.features.digital_twin.repositories.version_repository import VersionRepository
from app.features.digital_twin.services.entity_mappers import entity_to_response, entity_to_summary
from app.features.digital_twin.spatial.geometry import validate_coordinates
from app.shared.result import Failure, Result, Success


class EntityService:
    """Manages the complete entity lifecycle: create, update, state changes, versioning.

    Every state change emits an event and creates a version snapshot.
    """

    def __init__(
        self,
        entity_repo: EntityRepository,
        event_repo: EventRepository,
        version_repo: VersionRepository,
    ) -> None:
        self._entity_repo = entity_repo
        self._event_repo = event_repo
        self._version_repo = version_repo

    async def create_entity(self, req: CreateEntityRequest) -> Result:
        """Create a new entity with validation and initial versioning."""
        validate_coordinates(req.coordinates_lat, req.coordinates_lon)

        if req.max_capacity > 0 and req.current_capacity > req.max_capacity:
            return Failure(
                error_code="CAPACITY_EXCEEDED",
                message="Current capacity cannot exceed max capacity",
            )

        entity = Entity(
            name=req.name, description=req.description,
            entity_type=req.entity_type,
            venue_id=uuid.UUID(req.venue_id),
            zone_id=uuid.UUID(req.zone_id) if req.zone_id else None,
            parent_id=uuid.UUID(req.parent_id) if req.parent_id else None,
            coordinates_lat=req.coordinates_lat,
            coordinates_lon=req.coordinates_lon,
            indoor_x=req.indoor_x, indoor_y=req.indoor_y,
            floor_number=req.floor_number, building_level=req.building_level,
            current_capacity=req.current_capacity, max_capacity=req.max_capacity,
            accessibility_level=req.accessibility_level,
            accessibility_metadata=req.accessibility_metadata,
            metadata_json=req.metadata_json,
        )

        result = await self._entity_repo.create(entity)
        if not isinstance(result, Success):
            return Failure(error_code="CREATE_FAILED", message="Failed to create entity")

        await self._emit_event(entity.id, "entity_created", {"name": entity.name})
        await self._create_version(entity.id, entity, None)
        return Success(entity_to_response(entity))

    async def get_entity(self, entity_id: str) -> Result:
        """Fetch a single entity by ID."""
        result = await self._entity_repo.get_by_id(uuid.UUID(entity_id))
        if not isinstance(result, Success) or result.value is None:
            return Failure(error_code="ENTITY_NOT_FOUND", message=f"Entity '{entity_id}' not found")
        return Success(entity_to_response(result.value))

    async def update_entity(self, entity_id: str, req: UpdateEntityRequest) -> Result:
        """Update entity properties with validation."""
        result = await self._entity_repo.get_by_id(uuid.UUID(entity_id))
        if not isinstance(result, Success) or result.value is None:
            return Failure(error_code="ENTITY_NOT_FOUND", message=f"Entity '{entity_id}' not found")

        entity = result.value
        self._apply_update_fields(entity, req)

        await self._entity_repo.update(entity)
        await self._emit_event(entity.id, "entity_updated", {"fields": list(req.model_dump(exclude_none=True).keys())})
        await self._create_version(entity.id, entity, None)
        return Success(entity_to_response(entity))

    async def update_state(self, entity_id: str, req: UpdateEntityStateRequest) -> Result:
        """Update only real-time state fields. Optimized for high-frequency updates."""
        uid = uuid.UUID(entity_id)
        await self._entity_repo.update_state(
            uid,
            operational_status=req.operational_status,
            current_health=req.current_health,
            current_capacity=req.current_capacity,
            current_state=req.current_state,
        )
        await self._emit_event(uid, "state_changed", req.model_dump(exclude_none=True))
        return Success(None)

    async def bulk_update_state(self, req: BulkUpdateStateRequest) -> Result:
        """Update state for multiple entities using batch operations."""
        update_result = await self._entity_repo.batch_update_state(
            [uuid.UUID(eid) for eid in req.entity_ids],
            operational_status=req.operational_status,
            current_health=req.current_health,
            current_capacity=req.current_capacity,
            current_state=req.current_state,
        )
        if not isinstance(update_result, Success):
            return Failure(error_code="BULK_UPDATE_FAILED", message="Bulk state update failed")

        updated_count = update_result.value
        # Batch-emit events for all updated entities
        event_data = req.model_dump(exclude_none=True)
        events = [
            EntityEvent(entity_id=uid, event_type="state_changed", event_data=event_data, source="entity_service")
            for uid in [uuid.UUID(eid) for eid in req.entity_ids]
        ]
        if events:
            await self._event_repo.create_many(events)

        return Success({"updated_count": updated_count, "failed_ids": []})

    async def search_entities(self, req: dict) -> Result:
        """Search entities with filters and pagination."""
        search_req = SearchEntityRequest(**req)
        result = await self._entity_repo.search(
            entity_type=search_req.entity_type,
            operational_status=search_req.operational_status,
            current_health=search_req.current_health,
            zone_id=uuid.UUID(search_req.zone_id) if search_req.zone_id else None,
            venue_id=uuid.UUID(search_req.venue_id) if search_req.venue_id else None,
            search=search_req.search,
            page=search_req.page, page_size=search_req.page_size,
        )
        if not isinstance(result, Success):
            return Failure(error_code="SEARCH_FAILED", message="Entity search failed")

        entities, total = result.value
        total_pages = (total + search_req.page_size - 1) // search_req.page_size
        return Success(PaginatedEntityResponse(
            items=[entity_to_summary(e) for e in entities],
            total=total, page=search_req.page,
            page_size=search_req.page_size, total_pages=total_pages,
        ))

    async def delete_entity(self, entity_id: str) -> Result:
        """Soft-delete an entity."""
        uid = uuid.UUID(entity_id)
        result = await self._entity_repo.delete(uid)
        if isinstance(result, Success):
            await self._emit_event(uid, "entity_deleted", {})
        return result

    @staticmethod
    def _apply_update_fields(entity: Entity, req: UpdateEntityRequest) -> None:
        """Apply non-None update fields to an entity."""
        field_map = {
            "name": "name", "description": "description",
            "operational_status": "operational_status",
            "current_health": "current_health",
            "current_capacity": "current_capacity",
            "max_capacity": "max_capacity",
            "accessibility_level": "accessibility_level",
            "accessibility_metadata": "accessibility_metadata",
            "current_state": "current_state",
            "metadata_json": "metadata_json",
        }
        for req_field, entity_field in field_map.items():
            value = getattr(req, req_field)
            if value is not None:
                setattr(entity, entity_field, value)

        # Validate coordinates together before applying
        if req.coordinates_lat is not None or req.coordinates_lon is not None:
            lat = req.coordinates_lat if req.coordinates_lat is not None else entity.coordinates_lat
            lon = req.coordinates_lon if req.coordinates_lon is not None else entity.coordinates_lon
            validate_coordinates(lat, lon)
            entity.coordinates_lat = lat
            entity.coordinates_lon = lon
        if req.zone_id is not None:
            entity.zone_id = uuid.UUID(req.zone_id)
        if req.parent_id is not None:
            entity.parent_id = uuid.UUID(req.parent_id)

    async def _emit_event(self, entity_id: uuid.UUID, event_type: str, data: dict) -> None:
        """Append an event to the event log."""
        event = EntityEvent(
            entity_id=entity_id, event_type=event_type,
            event_data=data, source="entity_service",
        )
        await self._event_repo.create(event)

    async def _create_version(
        self, entity_id: uuid.UUID, entity: Entity, changed_by: uuid.UUID | None,
    ) -> None:
        """Create a versioned state snapshot. Silently skips on version computation failure."""
        next_version = await self._version_repo.get_next_version_number(entity_id)
        if not isinstance(next_version, Success):
            return  # Version number computation failed; skip versioning
        snapshot = {
            "name": entity.name,
            "entity_type": entity.entity_type.value,
            "operational_status": entity.operational_status.value,
            "current_health": entity.current_health.value,
            "current_capacity": entity.current_capacity,
            "max_capacity": entity.max_capacity,
            "coordinates_lat": float(entity.coordinates_lat),
            "coordinates_lon": float(entity.coordinates_lon),
            "metadata_json": entity.metadata_json,
        }
        version = EntityVersion(
            entity_id=entity_id, version=next_version.value,
            state_snapshot=snapshot, changed_by=changed_by,
        )
        await self._version_repo.create(version)
