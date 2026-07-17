"""Spatial service - nearby search, pathfinding, and bounding box queries."""

from __future__ import annotations

import asyncio
import time
import uuid

from app.features.digital_twin.dto.entity_responses import EntitySummaryResponse
from app.features.digital_twin.dto.spatial_requests import (
    CreateEdgeRequest,
    NearbySearchRequest,
    PathfindingRequest,
    SpatialBoundsRequest,
)
from app.features.digital_twin.dto.spatial_responses import (
    EdgeResponse,
    NearbyEntityResponse,
    NearbySearchResponse,
    PathfindingResponse,
    PathStepResponse,
)
from app.features.digital_twin.exceptions import PathNotFoundError
from app.features.digital_twin.models.edge import Edge, EdgeType
from app.features.digital_twin.repositories.edge_repository import EdgeRepository
from app.features.digital_twin.repositories.entity_repository import EntityRepository
from app.features.digital_twin.spatial.graph import GraphEdge, GraphNode, StadiumGraph
from app.shared.result import Failure, Result, Success

# In-memory graph cache with 60-second TTL to avoid rebuilding per-request.
_GRAPH_CACHE_TTL_SECONDS = 60.0
_graph_cache: dict[uuid.UUID, tuple[StadiumGraph, float]] = {}


class SpatialService:
    """Spatial queries, pathfinding, and graph operations."""

    def __init__(
        self,
        entity_repo: EntityRepository,
        edge_repo: EdgeRepository,
    ) -> None:
        self._entity_repo = entity_repo
        self._edge_repo = edge_repo

    async def nearby_search(self, req: NearbySearchRequest) -> Result:
        """Find entities within radius of a point."""
        result = await self._entity_repo.find_nearby(
            lat=req.latitude, lon=req.longitude,
            radius_meters=req.radius_meters,
            entity_type=req.entity_type, limit=req.limit,
        )
        if not isinstance(result, Success):
            return Failure(error_code="SEARCH_FAILED", message="Nearby search failed")

        entities = [
            NearbyEntityResponse(
                id=str(e.id), name=e.name,
                entity_type=e.entity_type.value,
                operational_status=e.operational_status.value,
                current_health=e.current_health.value,
                coordinates_lat=float(e.coordinates_lat),
                coordinates_lon=float(e.coordinates_lon),
                distance_meters=d,
            )
            for e, d in result.value
        ]
        return Success(NearbySearchResponse(
            entities=entities, query_lat=req.latitude,
            query_lon=req.longitude,
            radius_meters=req.radius_meters, count=len(entities),
        ))

    async def bounds_search(self, req: SpatialBoundsRequest) -> Result:
        """Find entities within a bounding box."""
        result = await self._entity_repo.find_in_bounds(
            lat_min=req.lat_min, lat_max=req.lat_max,
            lon_min=req.lon_min, lon_max=req.lon_max,
            entity_type=req.entity_type, limit=req.limit,
        )
        if not isinstance(result, Success):
            return Failure(error_code="SEARCH_FAILED", message="Bounds search failed")

        return Success([
            EntitySummaryResponse(
                id=str(e.id), name=e.name,
                entity_type=e.entity_type.value,
                operational_status=e.operational_status.value,
                current_health=e.current_health.value,
                current_capacity=e.current_capacity,
                max_capacity=e.max_capacity,
                coordinates_lat=float(e.coordinates_lat),
                coordinates_lon=float(e.coordinates_lon),
                zone_id=str(e.zone_id) if e.zone_id else None,
            )
            for e in result.value
        ])

    async def find_path(self, req: PathfindingRequest) -> Result:
        """Find shortest path between two entities using cached graph."""
        from_id = uuid.UUID(req.from_entity_id)
        to_id = uuid.UUID(req.to_entity_id)

        from_entity = await self._entity_repo.get_by_id(from_id)
        if not isinstance(from_entity, Success) or from_entity.value is None:
            return Failure(error_code="ENTITY_NOT_FOUND", message="Source entity not found")

        to_entity = await self._entity_repo.get_by_id(to_id)
        if not isinstance(to_entity, Success) or to_entity.value is None:
            return Failure(error_code="ENTITY_NOT_FOUND", message="Target entity not found")

        graph = await self._load_graph_cached(from_entity.value.venue_id)
        try:
            result = graph.find_shortest_path(
                start=from_id, end=to_id,
                accessibility_filter=req.accessibility_level,
                edge_type_filter=req.edge_type,
            )
        except PathNotFoundError as exc:
            return Failure(error_code="PATH_NOT_FOUND", message=str(exc))

        # Batch-fetch all entities on the path to avoid N+1
        entity_map = await self._batch_get_entities(result.path)

        steps: list[PathStepResponse] = []
        for i, eid in enumerate(result.path):
            entity_val = entity_map.get(eid)
            if entity_val is None:
                continue
            edge_type = result.edge_types[i - 1] if i > 0 else "start"
            steps.append(PathStepResponse(
                entity_id=str(eid),
                entity_name=entity_val["name"],
                entity_type=entity_val["entity_type"],
                coordinates_lat=entity_val["lat"],
                coordinates_lon=entity_val["lon"],
                edge_type=edge_type,
                distance_meters=0.0,
            ))

        return Success(PathfindingResponse(
            from_entity_id=req.from_entity_id,
            to_entity_id=req.to_entity_id,
            steps=steps,
            total_distance_meters=result.total_distance,
            total_steps=len(steps),
            accessibility_compliant=req.accessibility_level is None,
        ))

    async def create_edge(self, req: CreateEdgeRequest) -> Result:
        """Create a graph edge between two entities."""
        edge = Edge(
            from_entity_id=uuid.UUID(req.from_entity_id),
            to_entity_id=uuid.UUID(req.to_entity_id),
            edge_type=EdgeType(req.edge_type),
            weight=req.weight,
            is_bidirectional=req.is_bidirectional,
            accessibility_level=req.accessibility_level,
            venue_id=uuid.UUID(req.venue_id),
            metadata_json=req.metadata_json,
        )
        result = await self._edge_repo.create(edge)
        if not isinstance(result, Success):
            return Failure(error_code="CREATE_FAILED", message="Failed to create edge")
        # Invalidate graph cache for this venue
        _graph_cache.pop(uuid.UUID(req.venue_id), None)
        return Success(self._edge_to_response(edge))

    async def get_edges_for_venue(self, venue_id: str) -> Result:
        """Fetch all edges for a venue."""
        result = await self._edge_repo.get_by_venue(uuid.UUID(venue_id))
        if not isinstance(result, Success):
            return Failure(error_code="QUERY_FAILED", message="Failed to fetch edges")
        return Success([self._edge_to_response(e) for e in result.value])

    async def _load_graph_cached(self, venue_id: uuid.UUID) -> StadiumGraph:
        """Load graph from cache or rebuild if expired."""
        now = time.monotonic()
        cached = _graph_cache.get(venue_id)
        if cached and (now - cached[1]) < _GRAPH_CACHE_TTL_SECONDS:
            return cached[0]

        graph = await self._build_graph(venue_id)
        _graph_cache[venue_id] = (graph, now)
        return graph

    async def _build_graph(self, venue_id: uuid.UUID) -> StadiumGraph:
        """Load all entities and edges for a venue into an in-memory graph."""
        graph = StadiumGraph()

        entity_result = await self._entity_repo.search(
            venue_id=venue_id, page=1, page_size=100000,
        )
        if isinstance(entity_result, Success):
            for entity in entity_result.value[0]:
                graph.add_node(GraphNode(
                    entity_id=entity.id, name=entity.name,
                    entity_type=entity.entity_type.value,
                    lat=float(entity.coordinates_lat),
                    lon=float(entity.coordinates_lon),
                ))

        edge_result = await self._edge_repo.get_by_venue(venue_id)
        if isinstance(edge_result, Success):
            for edge in edge_result.value:
                graph.add_edge(GraphEdge(
                    from_id=edge.from_entity_id,
                    to_id=edge.to_entity_id,
                    edge_type=edge.edge_type.value,
                    weight=float(edge.weight),
                    accessibility_level=edge.accessibility_level.value,
                    is_bidirectional=edge.is_bidirectional,
                ))

        return graph

    async def _batch_get_entities(
        self, entity_ids: list[uuid.UUID],
    ) -> dict[uuid.UUID, dict]:
        """Fetch multiple entities at once to avoid N+1 queries."""
        result = await self._entity_repo.get_by_ids(entity_ids)
        if not isinstance(result, Success):
            return {}
        return {
            e.id: {
                "name": e.name,
                "entity_type": e.entity_type.value,
                "lat": float(e.coordinates_lat),
                "lon": float(e.coordinates_lon),
            }
            for e in result.value
        }

    def _edge_to_response(self, edge: Edge) -> EdgeResponse:
        return EdgeResponse(
            id=str(edge.id),
            from_entity_id=str(edge.from_entity_id),
            to_entity_id=str(edge.to_entity_id),
            edge_type=edge.edge_type.value,
            weight=float(edge.weight),
            is_bidirectional=edge.is_bidirectional,
            accessibility_level=edge.accessibility_level.value,
            venue_id=str(edge.venue_id),
        )
