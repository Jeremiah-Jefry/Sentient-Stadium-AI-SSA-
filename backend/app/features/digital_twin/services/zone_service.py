"""Zone service - hierarchy management and venue operations."""

from __future__ import annotations

import uuid

from app.features.digital_twin.dto.zone_requests import (
    CreateVenueRequest,
    CreateZoneRequest,
    UpdateZoneRequest,
)
from app.features.digital_twin.dto.zone_responses import (
    VenueResponse,
    ZoneResponse,
    ZoneTreeResponse,
)
from app.features.digital_twin.exceptions import CyclicZoneError, VenueNotFoundError, ZoneNotFoundError
from app.features.digital_twin.models.venue import Venue
from app.features.digital_twin.models.zone import Zone
from app.features.digital_twin.repositories.venue_repository import VenueRepository
from app.features.digital_twin.repositories.zone_repository import ZoneRepository
from app.shared.result import Failure, Result, Success


class ZoneService:
    """Manages zone hierarchy, venue CRUD, and tree operations."""

    def __init__(
        self, zone_repo: ZoneRepository, venue_repo: VenueRepository,
    ) -> None:
        self._zone_repo = zone_repo
        self._venue_repo = venue_repo

    async def create_venue(self, req: CreateVenueRequest) -> Result[VenueResponse]:
        """Create a new venue (stadium)."""
        venue = Venue(
            name=req.name, description=req.description,
            address=req.address,
            coordinates_lat=req.coordinates_lat,
            coordinates_lon=req.coordinates_lon,
            timezone=req.timezone,
            metadata_json=req.metadata_json,
        )
        result = await self._venue_repo.create(venue)
        if not isinstance(result, Success):
            return Failure(error_code="CREATE_FAILED", message="Failed to create venue")
        return Success(self._venue_to_response(venue))

    async def get_venue(self, venue_id: str) -> Result[VenueResponse]:
        """Fetch a venue by ID."""
        result = await self._venue_repo.get_by_id(uuid.UUID(venue_id))
        if not isinstance(result, Success) or result.value is None:
            return Failure(error_code="VENUE_NOT_FOUND", message=f"Venue '{venue_id}' not found")
        return Success(self._venue_to_response(result.value))

    async def list_venues(self) -> Result[list[VenueResponse]]:
        """List all venues."""
        result = await self._venue_repo.list_all()
        if not isinstance(result, Success):
            return Failure(error_code="LIST_FAILED", message="Failed to list venues")
        return Success([self._venue_to_response(v) for v in result.value])

    async def create_zone(self, req: CreateZoneRequest) -> Result[ZoneResponse]:
        """Create a new zone in the hierarchy."""
        venue_result = await self._venue_repo.get_by_id(uuid.UUID(req.venue_id))
        if not isinstance(venue_result, Success) or venue_result.value is None:
            return Failure(error_code="VENUE_NOT_FOUND", message="Parent venue not found")

        level = 0
        if req.parent_zone_id:
            parent_result = await self._zone_repo.get_by_id(uuid.UUID(req.parent_zone_id))
            if not isinstance(parent_result, Success) or parent_result.value is None:
                return Failure(error_code="ZONE_NOT_FOUND", message="Parent zone not found")
            level = parent_result.value.level + 1

        zone = Zone(
            name=req.name, description=req.description,
            zone_type=req.zone_type, level=level,
            parent_zone_id=uuid.UUID(req.parent_zone_id) if req.parent_zone_id else None,
            venue_id=uuid.UUID(req.venue_id),
            bounds_lat_min=req.bounds_lat_min,
            bounds_lat_max=req.bounds_lat_max,
            bounds_lon_min=req.bounds_lon_min,
            bounds_lon_max=req.bounds_lon_max,
            metadata_json=req.metadata_json,
        )

        result = await self._zone_repo.create(zone)
        if not isinstance(result, Success):
            return Failure(error_code="CREATE_FAILED", message="Failed to create zone")
        return Success(self._zone_to_response(zone))

    async def get_zone(self, zone_id: str) -> Result[ZoneResponse]:
        """Fetch a zone by ID."""
        result = await self._zone_repo.get_by_id(uuid.UUID(zone_id))
        if not isinstance(result, Success) or result.value is None:
            return Failure(error_code="ZONE_NOT_FOUND", message=f"Zone '{zone_id}' not found")
        return Success(self._zone_to_response(result.value))

    async def update_zone(self, zone_id: str, req: UpdateZoneRequest) -> Result[ZoneResponse]:
        """Update a zone with cycle detection."""
        result = await self._zone_repo.get_by_id(uuid.UUID(zone_id))
        if not isinstance(result, Success) or result.value is None:
            return Failure(error_code="ZONE_NOT_FOUND", message=f"Zone '{zone_id}' not found")

        zone = result.value
        if req.parent_zone_id is not None:
            new_parent = uuid.UUID(req.parent_zone_id)
            cycle_check = await self._zone_repo.would_create_cycle(zone.id, new_parent)
            if isinstance(cycle_check, Success) and cycle_check.value:
                return Failure(error_code="CYCLIC_ZONE_HIERARCHY", message="Operation would create a cycle")
            zone.parent_zone_id = new_parent

        if req.name is not None:
            zone.name = req.name
        if req.description is not None:
            zone.description = req.description
        if req.zone_type is not None:
            zone.zone_type = req.zone_type
        if req.bounds_lat_min is not None:
            zone.bounds_lat_min = req.bounds_lat_min
        if req.bounds_lat_max is not None:
            zone.bounds_lat_max = req.bounds_lat_max
        if req.bounds_lon_min is not None:
            zone.bounds_lon_min = req.bounds_lon_min
        if req.bounds_lon_max is not None:
            zone.bounds_lon_max = req.bounds_lon_max
        if req.metadata_json is not None:
            zone.metadata_json = req.metadata_json

        await self._zone_repo.update(zone)
        return Success(self._zone_to_response(zone))

    async def get_zone_tree(self, venue_id: str) -> Result[list[ZoneTreeResponse]]:
        """Build the full zone hierarchy tree for a venue."""
        root_result = await self._zone_repo.get_root_zones(uuid.UUID(venue_id))
        if not isinstance(root_result, Success):
            return Failure(error_code="TREE_FAILED", message="Failed to build zone tree")

        tree = []
        for root in root_result.value:
            node = await self._build_tree_node(root)
            tree.append(node)
        return Success(tree)

    async def get_descendants(self, zone_id: str) -> Result[list[ZoneResponse]]:
        """Get all descendant zones."""
        result = await self._zone_repo.get_descendants(uuid.UUID(zone_id))
        if not isinstance(result, Success):
            return Failure(error_code="QUERY_FAILED", message="Failed to get descendants")
        return Success([self._zone_to_response(z) for z in result.value])

    async def delete_zone(self, zone_id: str) -> Result[None]:
        """Soft-delete a zone."""
        return await self._zone_repo.delete(uuid.UUID(zone_id))

    async def _build_tree_node(self, zone: Zone) -> ZoneTreeResponse:
        """Recursively build a zone tree node."""
        children_result = await self._zone_repo.get_children(zone.id)
        children = []
        if isinstance(children_result, Success):
            for child in children_result.value:
                child_node = await self._build_tree_node(child)
                children.append(child_node)

        return ZoneTreeResponse(
            id=str(zone.id), name=zone.name,
            zone_type=zone.zone_type.value, level=zone.level,
            children=children,
        )

    def _venue_to_response(self, venue: Venue) -> VenueResponse:
        return VenueResponse(
            id=str(venue.id), name=venue.name,
            description=venue.description, address=venue.address,
            coordinates_lat=float(venue.coordinates_lat),
            coordinates_lon=float(venue.coordinates_lon),
            timezone=venue.timezone, metadata_json=venue.metadata_json,
            created_at=venue.created_at.isoformat() if venue.created_at else "",
            updated_at=venue.updated_at.isoformat() if venue.updated_at else "",
        )

    def _zone_to_response(self, zone: Zone) -> ZoneResponse:
        return ZoneResponse(
            id=str(zone.id), name=zone.name,
            description=zone.description,
            zone_type=zone.zone_type.value,
            level=zone.level,
            parent_zone_id=str(zone.parent_zone_id) if zone.parent_zone_id else None,
            venue_id=str(zone.venue_id),
            bounds_lat_min=float(zone.bounds_lat_min) if zone.bounds_lat_min is not None else None,
            bounds_lat_max=float(zone.bounds_lat_max) if zone.bounds_lat_max is not None else None,
            bounds_lon_min=float(zone.bounds_lon_min) if zone.bounds_lon_min is not None else None,
            bounds_lon_max=float(zone.bounds_lon_max) if zone.bounds_lon_max is not None else None,
            metadata_json=zone.metadata_json,
            created_at=zone.created_at.isoformat() if zone.created_at else "",
            updated_at=zone.updated_at.isoformat() if zone.updated_at else "",
        )
