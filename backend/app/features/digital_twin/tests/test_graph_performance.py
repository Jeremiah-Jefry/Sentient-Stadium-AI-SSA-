"""Concurrency and stress tests for the in-memory graph."""

import asyncio
import uuid
import time

import pytest

from app.features.digital_twin.spatial.graph import GraphEdge, GraphNode, StadiumGraph


def _uid() -> uuid.UUID:
    return uuid.uuid4()


class TestGraphPerformance:
    """Performance tests to verify graph operations meet sub-ms targets."""

    def _build_large_graph(self, node_count: int = 1000, edges_per_node: int = 5) -> StadiumGraph:
        """Build a large random graph for performance testing."""
        graph = StadiumGraph()
        nodes = []
        for i in range(node_count):
            nid = _uid()
            nodes.append(nid)
            graph.add_node(GraphNode(
                entity_id=nid, name=f"Entity-{i}",
                entity_type="gate",
                lat=40.0 + (i * 0.001),
                lon=-74.0 + (i * 0.001),
            ))

        import random
        random.seed(42)
        for nid in nodes:
            targets = random.sample(nodes, min(edges_per_node, len(nodes)))
            for target in targets:
                if target != nid:
                    graph.add_edge(GraphEdge(
                        from_id=nid, to_id=target, edge_type="walking",
                        weight=random.uniform(10, 500),
                        accessibility_level="full", is_bidirectional=True,
                    ))
        return graph

    def test_pathfinding_1000_nodes(self) -> None:
        """Dijkstra on 1000-node graph should complete in <100ms."""
        graph = self._build_large_graph(1000, 5)
        start = graph.get_node(list(graph._nodes.keys())[0])
        end = graph.get_node(list(graph._nodes.keys())[-1])

        t0 = time.perf_counter()
        result = graph.find_shortest_path(start.entity_id, end.entity_id)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        assert result.path[0] == start.entity_id
        assert result.path[-1] == end.entity_id
        assert elapsed_ms < 100, f"Pathfinding took {elapsed_ms:.1f}ms (>100ms target)"

    def test_connected_components_1000_nodes(self) -> None:
        """Connected components computation should complete in <50ms."""
        graph = self._build_large_graph(1000, 3)

        t0 = time.perf_counter()
        components = graph.get_connected_components()
        elapsed_ms = (time.perf_counter() - t0) * 1000

        assert components >= 1
        assert elapsed_ms < 50, f"Component analysis took {elapsed_ms:.1f}ms"

    def test_concurrent_pathfinding(self) -> None:
        """Multiple concurrent pathfinding requests should not corrupt state."""
        graph = self._build_large_graph(500, 4)
        node_ids = list(graph._nodes.keys())

        async def find_path() -> list[uuid.UUID]:
            start = node_ids[0]
            end = node_ids[-1]
            result = graph.find_shortest_path(start, end)
            return result.path

        async def run_all() -> None:
            tasks = [find_path() for _ in range(50)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in results:
                if isinstance(r, Exception):
                    raise r
                assert len(r) > 0

        asyncio.run(run_all())

    def test_graph_stats(self) -> None:
        """Graph statistics should be computed efficiently."""
        graph = self._build_large_graph(200, 4)

        t0 = time.perf_counter()
        node_count = graph.node_count
        edge_count = graph.edge_count
        components = graph.get_connected_components()
        isolated = graph.get_isolated_nodes()
        elapsed_ms = (time.perf_counter() - t0) * 1000

        assert node_count == 200
        assert edge_count > 0
        assert components >= 1
        assert elapsed_ms < 50
