"""In-memory navigation graph with dynamic weight computation.

Extends Module 2's StadiumGraph concept with:
- Dynamic edge weights from realtime conditions
- Multi-dimensional cost model
- Incremental graph updates
- Spatial indexing for proximity queries
"""

from __future__ import annotations

import heapq
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass

from app.features.navigation.exceptions import (
    NodeNotFoundError,
    RouteNotFoundError,
)
from app.features.navigation.graph.models import (
    NavEdge,
    NavNode,
    PathResult,
    WeightContext,
)


@dataclass(frozen=True, slots=True)
class AdjacencyEntry:
    """A single entry in the adjacency list with full edge metadata."""

    to_id: uuid.UUID
    edge_type: str
    base_weight: float
    accessibility_level: str
    distance_meters: float
    floor_change: int
    is_bidirectional: bool


class NavigationGraph:
    """In-memory adjacency list navigation graph with dynamic weights.

    Supports:
    - Dynamic edge weight computation from WeightContext
    - Multi-objective cost evaluation
    - Spatial indexing for proximity queries
    - Incremental node/edge updates
    - Snapshot-based cache invalidation
    """

    def __init__(self) -> None:
        self._nodes: dict[uuid.UUID, NavNode] = {}
        self._adjacency: dict[uuid.UUID, list[AdjacencyEntry]] = defaultdict(list)
        self._edge_index: dict[tuple[uuid.UUID, uuid.UUID], AdjacencyEntry] = {}
        self._spatial_index: list[tuple[float, float, uuid.UUID]] = []
        self._version: int = 0
        self._loaded_at: float = 0.0

    def add_node(self, node: NavNode) -> None:
        self._nodes[node.node_id] = node

    def add_edge(self, edge: NavEdge) -> None:
        entry = AdjacencyEntry(
            to_id=edge.to_id,
            edge_type=edge.edge_type,
            base_weight=edge.base_weight,
            accessibility_level=edge.accessibility_level,
            distance_meters=edge.distance_meters,
            floor_change=edge.floor_change,
            is_bidirectional=edge.is_bidirectional,
        )
        self._adjacency[edge.from_id].append(entry)
        self._edge_index[(edge.from_id, edge.to_id)] = entry

        if edge.is_bidirectional:
            rev = AdjacencyEntry(
                to_id=edge.from_id,
                edge_type=edge.edge_type,
                base_weight=edge.base_weight,
                accessibility_level=edge.accessibility_level,
                distance_meters=edge.distance_meters,
                floor_change=-edge.floor_change,
                is_bidirectional=True,
            )
            self._adjacency[edge.to_id].append(rev)
            self._edge_index[(edge.to_id, edge.from_id)] = rev

        self._version += 1

    def update_node(self, node: NavNode) -> None:
        if node.node_id in self._nodes:
            self._nodes[node.node_id] = node
            self._version += 1

    def remove_node(self, node_id: uuid.UUID) -> bool:
        if node_id not in self._nodes:
            return False
        del self._nodes[node_id]
        self._adjacency.pop(node_id, None)
        self._edge_index = {
            k: v for k, v in self._edge_index.items()
            if k[0] != node_id and k[1] != node_id
        }
        for nid, adj_list in list(self._adjacency.items()):
            self._adjacency[nid] = [
                e for e in adj_list if e.to_id != node_id
            ]
        self._version += 1
        return True

    def get_node(self, node_id: uuid.UUID) -> NavNode | None:
        return self._nodes.get(node_id)

    def get_neighbors(self, node_id: uuid.UUID) -> list[AdjacencyEntry]:
        return self._adjacency.get(node_id, [])

    def compute_edge_cost(
        self,
        entry: AdjacencyEntry,
        ctx: WeightContext,
    ) -> float:
        """Compute dynamic weight for an edge given current conditions."""
        if ctx.temporarily_closed:
            return float("inf")
        if ctx.emergency_active and entry.edge_type not in ("emergency", "walking"):
            return float("inf")
        if ctx.security_restricted and entry.edge_type == "staff_only":
            return float("inf")
        if entry.accessibility_level == "none":
            return float("inf")

        cost = entry.base_weight

        if ctx.crowd_density > 0.3:
            cost *= 1.0 + (ctx.crowd_density * 2.0)
        if ctx.walking_speed_modifier <= 0:
            return float("inf")
        cost /= ctx.walking_speed_modifier
        if ctx.weather_penalty > 0:
            cost *= 1.0 + ctx.weather_penalty
        if entry.edge_type == "escalator" and not ctx.escalator_available:
            return float("inf")
        if entry.edge_type == "elevator" and not ctx.elevator_available:
            return float("inf")
        if entry.floor_change != 0:
            cost *= 1.0 + abs(entry.floor_change) * 0.3
        if ctx.risk_score > 0.5:
            cost *= 1.0 + ctx.risk_score
        if ctx.predicted_congestion > 0.3:
            cost *= 1.0 + ctx.predicted_congestion
        if ctx.waiting_time_seconds > 0:
            cost += ctx.waiting_time_seconds
        cost *= max(ctx.energy_cost_modifier, 0.1)

        return max(cost, 0.001)

    def find_shortest_path(
        self,
        start: uuid.UUID,
        end: uuid.UUID,
        ctx: WeightContext | None = None,
        accessibility_filter: str | None = None,
        edge_type_filter: str | None = None,
    ) -> PathResult:
        """Dijkstra shortest path with dynamic weights and filtering."""
        if start not in self._nodes:
            raise NodeNotFoundError(str(start))
        if end not in self._nodes:
            raise NodeNotFoundError(str(end))

        weight_ctx = ctx or WeightContext()
        t_start = time.monotonic()

        distances: dict[uuid.UUID, float] = {start: 0.0}
        predecessors: dict[uuid.UUID, uuid.UUID | None] = {start: None}
        edge_used: dict[uuid.UUID, str] = {}
        visited: set[uuid.UUID] = set()
        heap: list[tuple[float, uuid.UUID]] = [(0.0, start)]
        nodes_visited = 0

        while heap:
            dist, current = heapq.heappop(heap)
            if current in visited:
                continue
            visited.add(current)
            nodes_visited += 1

            if current == end:
                elapsed = (time.monotonic() - t_start) * 1000
                return self._build_path_result(
                    start, end, predecessors, edge_used,
                    dist, nodes_visited, elapsed,
                )

            for entry in self._adjacency.get(current, []):
                if entry.to_id in visited:
                    continue
                if edge_type_filter and entry.edge_type != edge_type_filter:
                    continue
                if (accessibility_filter
                        and entry.accessibility_level not in (accessibility_filter, "full")):
                    continue

                edge_cost = self.compute_edge_cost(entry, weight_ctx)
                if edge_cost == float("inf"):
                    continue

                new_dist = dist + edge_cost
                if new_dist < distances.get(entry.to_id, float("inf")):
                    distances[entry.to_id] = new_dist
                    predecessors[entry.to_id] = current
                    edge_used[entry.to_id] = entry.edge_type
                    heapq.heappush(heap, (new_dist, entry.to_id))

        raise RouteNotFoundError(
            details={"start": str(start), "end": str(end)},
        )

    def find_k_shortest(
        self,
        start: uuid.UUID,
        end: uuid.UUID,
        k: int = 3,
        ctx: WeightContext | None = None,
    ) -> list[PathResult]:
        """Yen's K-shortest paths algorithm.

        Temporarily removes shared edges during spur computation
        to force exploration of alternative routes.
        """
        if start not in self._nodes or end not in self._nodes:
            raise RouteNotFoundError(
                details={"start": str(start), "end": str(end)},
            )

        weight_ctx = ctx or WeightContext()
        results: list[PathResult] = []
        paths_seen: set[tuple[uuid.UUID, ...]] = set()

        first = self.find_shortest_path(start, end, weight_ctx)
        results.append(first)
        paths_seen.add(tuple(first.path))

        for _i in range(1, k):
            prev_path = results[-1].path
            for j in range(len(prev_path) - 1):
                spur_node = prev_path[j]
                root_path = prev_path[: j + 1]

                removed_entries: list[
                    tuple[
                        tuple[uuid.UUID, uuid.UUID],
                        AdjacencyEntry,
                    ]
                ] = []
                for r in results:
                    r_path = r.path
                    if len(r_path) > j and r_path[: j + 1] == root_path:
                        edge_key = (r_path[j], r_path[j + 1])
                        if edge_key in self._edge_index:
                            entry = self._edge_index.pop(edge_key)
                            removed_entries.append((edge_key, entry))
                            adj_list = self._adjacency.get(edge_key[0], [])
                            self._adjacency[edge_key[0]] = [
                                e for e in adj_list
                                if e.to_id != edge_key[1]
                            ]

                try:
                    spur_result = self.find_shortest_path(
                        spur_node, end, weight_ctx,
                    )
                    total_path = list(root_path[:-1]) + spur_result.path

                    root_edges = []
                    root_dist = 0.0
                    for ri in range(len(root_path) - 1):
                        rk = (root_path[ri], root_path[ri + 1])
                        re = self._edge_index.get(rk)
                        if re is not None:
                            root_dist += re.distance_meters
                        root_edges.append(
                            re.edge_type if re else "walking",
                        )

                    total_edges = root_edges + spur_result.edges
                    total_dist = (
                        root_dist
                        + spur_result.total_distance_meters
                    )
                    total_cost = (
                        self._sum_edge_cost(root_path, weight_ctx)
                        + spur_result.total_cost
                    )
                    path_tuple = tuple(total_path)
                    if path_tuple not in paths_seen:
                        candidate = PathResult(
                            path=total_path,
                            edges=total_edges,
                            total_distance_meters=total_dist,
                            total_time_seconds=total_cost,
                            total_cost=total_cost,
                            algorithm_used="yen_k_shortest",
                        )
                        results.append(candidate)
                        paths_seen.add(path_tuple)
                except (RouteNotFoundError, NodeNotFoundError):
                    continue
                finally:
                    for ek, entry in removed_entries:
                        self._edge_index[ek] = entry
                        self._adjacency[ek[0]].append(entry)

            if len(results) >= k:
                break

        results.sort(key=lambda r: r.total_cost)
        return results[:k]

    def _sum_edge_cost(
        self,
        path: list[uuid.UUID],
        ctx: WeightContext,
    ) -> float:
        """Sum dynamic edge costs along a path."""
        total = 0.0
        for i in range(len(path) - 1):
            entry = self._edge_index.get((path[i], path[i + 1]))
            if entry is not None:
                total += self.compute_edge_cost(entry, ctx)
        return total

    def find_nearest(
        self,
        from_id: uuid.UUID,
        target_types: set[str],
        ctx: WeightContext | None = None,
    ) -> tuple[NavNode, float] | None:
        """Find nearest node of given types using Dijkstra."""
        if from_id not in self._nodes:
            raise NodeNotFoundError(str(from_id))

        weight_ctx = ctx or WeightContext()
        distances: dict[uuid.UUID, float] = {from_id: 0.0}
        visited: set[uuid.UUID] = set()
        heap: list[tuple[float, uuid.UUID]] = [(0.0, from_id)]

        while heap:
            dist, current = heapq.heappop(heap)
            if current in visited:
                continue
            visited.add(current)

            node = self._nodes.get(current)
            if node and node.entity_type in target_types and current != from_id:
                return node, dist

            for entry in self._adjacency.get(current, []):
                if entry.to_id in visited:
                    continue
                edge_cost = self.compute_edge_cost(entry, weight_ctx)
                if edge_cost == float("inf"):
                    continue
                new_dist = dist + edge_cost
                if new_dist < distances.get(entry.to_id, float("inf")):
                    distances[entry.to_id] = new_dist
                    heapq.heappush(heap, (new_dist, entry.to_id))

        return None

    def find_within_radius(
        self,
        center_id: uuid.UUID,
        radius: float,
        target_types: set[str] | None = None,
        ctx: WeightContext | None = None,
    ) -> list[tuple[NavNode, float]]:
        """Find all nodes within cost radius of center."""
        if center_id not in self._nodes:
            raise NodeNotFoundError(str(center_id))

        weight_ctx = ctx or WeightContext()
        distances: dict[uuid.UUID, float] = {center_id: 0.0}
        visited: set[uuid.UUID] = set()
        heap: list[tuple[float, uuid.UUID]] = [(0.0, center_id)]
        results: list[tuple[NavNode, float]] = []

        while heap:
            dist, current = heapq.heappop(heap)
            if dist > radius:
                break
            if current in visited:
                continue
            visited.add(current)

            node = self._nodes.get(current)
            if (node and current != center_id
                    and (target_types is None or node.entity_type in target_types)):
                results.append((node, dist))

            for entry in self._adjacency.get(current, []):
                if entry.to_id in visited:
                    continue
                edge_cost = self.compute_edge_cost(entry, weight_ctx)
                if edge_cost == float("inf"):
                    continue
                new_dist = dist + edge_cost
                if new_dist < distances.get(entry.to_id, float("inf")):
                    distances[entry.to_id] = new_dist
                    heapq.heappush(heap, (new_dist, entry.to_id))

        results.sort(key=lambda x: x[1])
        return results

    def _build_path_result(
        self,
        _start: uuid.UUID,
        end: uuid.UUID,
        predecessors: dict[uuid.UUID, uuid.UUID | None],
        edge_used: dict[uuid.UUID, str],
        total_cost: float,
        nodes_visited: int,
        elapsed_ms: float,
        algorithm_name: str = "dijkstra",
    ) -> PathResult:
        path: list[uuid.UUID] = []
        edges: list[str] = []
        current: uuid.UUID | None = end

        while current is not None:
            path.append(current)
            if current in edge_used:
                edges.append(edge_used[current])
            current = predecessors.get(current)

        path.reverse()
        edges.reverse()

        total_dist = 0.0
        for i in range(len(path) - 1):
            entry = self._edge_index.get((path[i], path[i + 1]))
            if entry:
                total_dist += entry.distance_meters

        return PathResult(
            path=path,
            edges=edges,
            total_distance_meters=total_dist,
            total_time_seconds=total_cost,
            total_cost=total_cost,
            algorithm_used=algorithm_name,
            nodes_visited=nodes_visited,
            computation_ms=elapsed_ms,
        )

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        return sum(len(v) for v in self._adjacency.values())

    @property
    def version(self) -> int:
        return self._version

    def clear(self) -> None:
        self._nodes.clear()
        self._adjacency.clear()
        self._edge_index.clear()
        self._spatial_index.clear()
        self._version = 0
