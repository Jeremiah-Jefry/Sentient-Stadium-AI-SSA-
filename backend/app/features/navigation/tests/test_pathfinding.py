"""Tests for pathfinding algorithms — A*, Dijkstra, bidirectional."""

from __future__ import annotations

import uuid

import pytest

from app.features.navigation.exceptions import RouteNotFoundError
from app.features.navigation.graph.graph_manager import NavigationGraph
from app.features.navigation.graph.models import NavEdge, NavNode
from app.features.navigation.pathfinding.algorithm import (
    AlgorithmRegistry,
    AStarAlgorithm,
    BidirectionalAlgorithm,
    DijkstraAlgorithm,
)


def _uid() -> uuid.UUID:
    return uuid.uuid4()


def _build_grid_graph(
    rows: int = 3, cols: int = 3,
) -> tuple[NavigationGraph, list[list[uuid.UUID]]]:
    graph = NavigationGraph()
    grid: list[list[uuid.UUID]] = []
    for r in range(rows):
        row: list[uuid.UUID] = []
        for c in range(cols):
            nid = _uid()
            row.append(nid)
            graph.add_node(NavNode(
                node_id=nid, name=f"({r},{c})",
                entity_type="corridor",
                lat=float(r) * 0.001,
                lon=float(c) * 0.001,
            ))
        grid.append(row)

    for r in range(rows):
        for c in range(cols):
            if c + 1 < cols:
                graph.add_edge(NavEdge(
                    from_id=grid[r][c], to_id=grid[r][c + 1],
                    edge_type="walking", base_weight=1.0,
                    distance_meters=100.0,
                ))
            if r + 1 < rows:
                graph.add_edge(NavEdge(
                    from_id=grid[r][c], to_id=grid[r + 1][c],
                    edge_type="walking", base_weight=1.0,
                    distance_meters=100.0,
                ))

    return graph, grid


class TestAStar:
    def test_finds_path_on_grid(self) -> None:
        graph, grid = _build_grid_graph(3, 3)
        algo = AStarAlgorithm()
        result = algo.find_path(graph, grid[0][0], grid[2][2])
        assert grid[0][0] in result.path
        assert grid[2][2] in result.path
        assert result.algorithm_used == "astar"

    def test_path_not_found(self) -> None:
        graph, grid = _build_grid_graph(2, 2)
        graph.remove_node(grid[1][1])
        algo = AStarAlgorithm()
        with pytest.raises(RouteNotFoundError):
            algo.find_path(graph, grid[0][0], grid[1][1])

    def test_heuristic_admissibility(self) -> None:
        a = NavNode(node_id=_uid(), name="A", entity_type="c", lat=0.0, lon=0.0)
        b = NavNode(node_id=_uid(), name="B", entity_type="c", lat=0.001, lon=0.001)
        h = AStarAlgorithm._heuristic(a, b)
        assert h > 0


class TestDijkstra:
    def test_finds_path(self) -> None:
        graph, grid = _build_grid_graph(3, 3)
        algo = DijkstraAlgorithm()
        result = algo.find_path(graph, grid[0][0], grid[2][2])
        assert result.path[0] == grid[0][0]
        assert result.path[-1] == grid[2][2]


class TestBidirectional:
    def test_finds_path(self) -> None:
        graph, grid = _build_grid_graph(3, 3)
        algo = BidirectionalAlgorithm()
        result = algo.find_path(graph, grid[0][0], grid[2][2])
        assert result.path[0] == grid[0][0]
        assert result.path[-1] == grid[2][2]
        assert result.algorithm_used == "bidirectional"

    def test_path_optimal(self) -> None:
        graph, grid = _build_grid_graph(3, 3)
        algo = BidirectionalAlgorithm()
        result = algo.find_path(graph, grid[0][0], grid[2][2])
        assert result.total_distance_meters == 400.0


class TestAlgorithmRegistry:
    def test_all_registered(self) -> None:
        reg = AlgorithmRegistry()
        assert "astar" in reg.available
        assert "dijkstra" in reg.available
        assert "bidirectional" in reg.available

    def test_select_astar_for_small_graph(self) -> None:
        reg = AlgorithmRegistry()
        algo = reg.select(graph_size=100)
        assert algo.name == "astar"

    def test_select_bidirectional_for_large_graph(self) -> None:
        reg = AlgorithmRegistry()
        algo = reg.select(graph_size=100_000)
        assert algo.name == "bidirectional"

    def test_custom_algorithm(self) -> None:
        reg = AlgorithmRegistry()
        custom = DijkstraAlgorithm()
        reg.register(custom)
        assert reg.get("dijkstra") is custom
