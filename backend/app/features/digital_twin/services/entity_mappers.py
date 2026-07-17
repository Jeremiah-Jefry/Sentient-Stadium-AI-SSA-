"""Entity model-to-response mapping utilities."""

from __future__ import annotations

from app.features.digital_twin.dto.entity_responses import (
    EntityResponse,
    EntitySummaryResponse,
)
from app.features.digital_twin.models.entity import Entity


def entity_to_response(entity: Entity) -> EntityResponse:
    """Convert an entity model to a full API response."""
    return EntityResponse(
        id=str(entity.id), name=entity.name,
        description=entity.description,
        entity_type=entity.entity_type.value,
        operational_status=entity.operational_status.value,
        current_health=entity.current_health.value,
        current_capacity=entity.current_capacity,
        max_capacity=entity.max_capacity,
        coordinates_lat=float(entity.coordinates_lat),
        coordinates_lon=float(entity.coordinates_lon),
        indoor_x=float(entity.indoor_x) if entity.indoor_x else None,
        indoor_y=float(entity.indoor_y) if entity.indoor_y else None,
        floor_number=entity.floor_number,
        building_level=entity.building_level,
        accessibility_level=entity.accessibility_level.value,
        accessibility_metadata=entity.accessibility_metadata,
        current_state=entity.current_state,
        metadata_json=entity.metadata_json,
        venue_id=str(entity.venue_id),
        zone_id=str(entity.zone_id) if entity.zone_id else None,
        parent_id=str(entity.parent_id) if entity.parent_id else None,
        components=[],
        created_at=entity.created_at.isoformat() if entity.created_at else "",
        updated_at=entity.updated_at.isoformat() if entity.updated_at else "",
    )


def entity_to_summary(entity: Entity) -> EntitySummaryResponse:
    """Convert an entity model to a lightweight summary response."""
    return EntitySummaryResponse(
        id=str(entity.id), name=entity.name,
        entity_type=entity.entity_type.value,
        operational_status=entity.operational_status.value,
        current_health=entity.current_health.value,
        current_capacity=entity.current_capacity,
        max_capacity=entity.max_capacity,
        coordinates_lat=float(entity.coordinates_lat),
        coordinates_lon=float(entity.coordinates_lon),
        zone_id=str(entity.zone_id) if entity.zone_id else None,
    )
