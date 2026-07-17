"""In-memory graph model for fast pathfinding and connectivity analysis."""

from __future__ import annotations

import heapq
import uuid
from collections import defaultdict
from dataclasses import dataclass, field

from app.features.digital_twin.exceptions import PathNotFoundError


@dataclass(frozen=True, slots=True)
class GraphNode:
    """A node in the in-memory graph with spatial coordinates."""

    entity_id: uuid.UUID
    name: str
    entity_type: str
    lat: float
    lon: float


@dataclass(frozen=True, slots=True)
class GraphEdge:
    """A weighted directed edge in the in-memory graph."""

    from_id: uuid.UUID
    to_id: uuid.UUID
    edge_type: str
    weight: float
    accessibility_level: str
    is_bidirectional: bool


@dataclass(slots=True)
class PathResult:
    """Result of a pathfinding computation."""

    path: list[uuid.UUID]
    total_distance: float
    edge_types: list[str]


class StadiumGraph:
    """In-memory adjacency list representation of the stadium spatial graph.

    Loaded from database edges. Supports Dijkstra shortest path with
    edge-type and accessibility filtering.
    """

    def __init__(self) -> None:
        self._nodes: dict[uuid.UUID, GraphNode] = {}
        self._adjacency: dict[uuid.UUID, list[tuple[uuid.UUID, float, str, str]]] = defaultdict(list)

    def add_node(self, node: GraphNode) -> None:
        """Register a node in the graph."""
        self._nodes[node.entity_id] = node

    def add_edge(self, edge: GraphEdge) -> None:
        """Add an edge to the adjacency list."""
        self._adjacency[edge.from_id].append(
            (edge.to_id, edge.weight, edge.edge_type, edge.accessibility_level),
        )
        if edge.is_bidirectional:
            self._adjacency[edge.to_id].append(
                (edge.from_id, edge.weight, edge.edge_type, edge.accessibility_level),
            )

    def get_node(self, node_id: uuid.UUID) -> GraphNode | None:
        """Retrieve a node by ID."""
        return self._nodes.get(node_id)

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        return sum(len(neighbors) for neighbors in self._adjacency.values())

    def find_shortest_path(
        self,
        start: uuid.UUID,
        end: uuid.UUID,
        accessibility_filter: str | None = None,
        edge_type_filter: str | None = None,
    ) -> PathResult:
        """Dijkstra shortest path with optional filtering.

        Raises PathNotFoundError if no path exists.
        """
        if start not in self._nodes or end not in self._nodes:
            raise PathNotFoundError(
                details={"start": str(start), "end": str(end), "reason": "Entity not in graph"},
            )

        distances: dict[uuid.UUID, float] = {start: 0.0}
        predecessors: dict[uuid.UUID, uuid.UUID | None] = {start: None}
        edge_used: dict[uuid.UUID, str] = {}
        visited: set[uuid.UUID] = set()
        heap: list[tuple[float, uuid.UUID]] = [(0.0, start)]

        while heap:
            dist, current = heapq.heappop(heap)

            if current in visited:
                continue
            visited.add(current)

            if current == end:
                return self._reconstruct_path(start, end, predecessors, edge_used, dist)

            for neighbor, weight, edge_type, access_level in self._adjacency.get(current, []):
                if neighbor in visited:
                    continue
                if edge_type_filter and edge_type != edge_type_filter:
                    continue
                if accessibility_filter and access_level not in (accessibility_filter, "full"):
                    continue

                new_dist = dist + weight
                if new_dist < distances.get(neighbor, float("inf")):
                    distances[neighbor] = new_dist
                    predecessors[neighbor] = current
                    edge_used[neighbor] = edge_type
                    heapq.heappush(heap, (new_dist, neighbor))

        raise PathNotFoundError(
            details={"start": str(start), "end": str(end), "reason": "No path exists"},
        )

    def _reconstruct_path(
        self,
        start: uuid.UUID,
        end: uuid.UUID,
        predecessors: dict[uuid.UUID, uuid.UUID | None],
        edge_used: dict[uuid.UUID, str],
        total_distance: float,
    ) -> PathResult:
        """Walk backwards from end to start to build the path."""
        path: list[uuid.UUID] = []
        edge_types: list[str] = []
        current: uuid.UUID | None = end

        while current is not None:
            path.append(current)
            if current in edge_used:
                edge_types.append(edge_used[current])
            current = predecessors.get(current)

        path.reverse()
        edge_types.reverse()
        return PathResult(
            path=path,
            total_distance=total_distance,
            edge_types=edge_types,
        )

    def get_connected_components(self) -> int:
        """Count connected components using BFS."""
        visited: set[uuid.UUID] = set()
        components = 0

        for node_id in self._nodes:
            if node_id in visited:
                continue
            components += 1
            queue = [node_id]
            while queue:
                current = queue.pop()
                if current in visited:
                    continue
                visited.add(current)
                for neighbor, _, _, _ in self._adjacency.get(current, []):
                    if neighbor not in visited:
                        queue.append(neighbor)

        return components

    def get_degree(self, node_id: uuid.UUID) -> int:
        """Get the degree of a node."""
        return len(self._adjacency.get(node_id, []))

    def get_isolated_nodes(self) -> list[uuid.UUID]:
        """Find nodes with no edges."""
        return [nid for nid in self._nodes if not self._adjacency.get(nid)]
