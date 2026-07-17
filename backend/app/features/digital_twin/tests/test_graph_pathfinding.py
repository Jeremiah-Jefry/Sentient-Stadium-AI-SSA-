"""Unit tests for in-memory graph and Dijkstra pathfinding."""

import uuid

import pytest

from app.features.digital_twin.exceptions import PathNotFoundError
from app.features.digital_twin.spatial.graph import GraphEdge, GraphNode, StadiumGraph


def _uid() -> uuid.UUID:
    return uuid.uuid4()


class TestStadiumGraph:
    def test_add_node(self) -> None:
        graph = StadiumGraph()
        node_id = _uid()
        graph.add_node(GraphNode(
            entity_id=node_id, name="Gate A",
            entity_type="gate", lat=40.0, lon=-74.0,
        ))
        assert graph.node_count == 1
        assert graph.get_node(node_id) is not None

    def test_add_edge(self) -> None:
        graph = StadiumGraph()
        a, b = _uid(), _uid()
        graph.add_node(GraphNode(entity_id=a, name="A", entity_type="gate", lat=40.0, lon=-74.0))
        graph.add_node(GraphNode(entity_id=b, name="B", entity_type="gate", lat=40.1, lon=-74.1))
        graph.add_edge(GraphEdge(
            from_id=a, to_id=b, edge_type="walking",
            weight=100.0, accessibility_level="full", is_bidirectional=True,
        ))
        assert graph.edge_count == 2  # Bidirectional = 2 directed edges

    def test_shortest_path_direct(self) -> None:
        graph = StadiumGraph()
        a, b = _uid(), _uid()
        graph.add_node(GraphNode(entity_id=a, name="A", entity_type="gate", lat=40.0, lon=-74.0))
        graph.add_node(GraphNode(entity_id=b, name="B", entity_type="gate", lat=40.1, lon=-74.1))
        graph.add_edge(GraphEdge(
            from_id=a, to_id=b, edge_type="walking",
            weight=100.0, accessibility_level="full", is_bidirectional=True,
        ))
        result = graph.find_shortest_path(a, b)
        assert result.path == [a, b]
        assert result.total_distance == 100.0

    def test_shortest_path_chooses_shorter_route(self) -> None:
        graph = StadiumGraph()
        a, b, c, d = _uid(), _uid(), _uid(), _uid()

        for nid, name in [(a, "A"), (b, "B"), (c, "C"), (d, "D")]:
            graph.add_node(GraphNode(entity_id=nid, name=name, entity_type="gate", lat=40.0, lon=-74.0))

        # Direct: A -> D = 300
        graph.add_edge(GraphEdge(from_id=a, to_id=d, edge_type="walking",
                                 weight=300.0, accessibility_level="full", is_bidirectional=False))
        # Via B, C: A -> B (50) -> C (50) -> D (50) = 150
        graph.add_edge(GraphEdge(from_id=a, to_id=b, edge_type="walking",
                                 weight=50.0, accessibility_level="full", is_bidirectional=False))
        graph.add_edge(GraphEdge(from_id=b, to_id=c, edge_type="walking",
                                 weight=50.0, accessibility_level="full", is_bidirectional=False))
        graph.add_edge(GraphEdge(from_id=c, to_id=d, edge_type="walking",
                                 weight=50.0, accessibility_level="full", is_bidirectional=False))

        result = graph.find_shortest_path(a, d)
        assert result.path == [a, b, c, d]
        assert result.total_distance == 150.0

    def test_shortest_path_no_route(self) -> None:
        graph = StadiumGraph()
        a, b = _uid(), _uid()
        graph.add_node(GraphNode(entity_id=a, name="A", entity_type="gate", lat=40.0, lon=-74.0))
        graph.add_node(GraphNode(entity_id=b, name="B", entity_type="gate", lat=40.1, lon=-74.1))
        with pytest.raises(PathNotFoundError):
            graph.find_shortest_path(a, b)

    def test_shortest_path_same_node(self) -> None:
        graph = StadiumGraph()
        a = _uid()
        graph.add_node(GraphNode(entity_id=a, name="A", entity_type="gate", lat=40.0, lon=-74.0))
        result = graph.find_shortest_path(a, a)
        assert result.path == [a]
        assert result.total_distance == 0.0

    def test_path_unknown_start_node(self) -> None:
        graph = StadiumGraph()
        a, b = _uid(), _uid()
        graph.add_node(GraphNode(entity_id=b, name="B", entity_type="gate", lat=40.1, lon=-74.1))
        with pytest.raises(PathNotFoundError):
            graph.find_shortest_path(a, b)

    def test_connected_components(self) -> None:
        graph = StadiumGraph()
        a, b, c, d = _uid(), _uid(), _uid(), _uid()

        for nid in [a, b, c, d]:
            graph.add_node(GraphNode(entity_id=nid, name="N", entity_type="gate", lat=40.0, lon=-74.0))

        graph.add_edge(GraphEdge(from_id=a, to_id=b, edge_type="walking",
                                 weight=10.0, accessibility_level="full", is_bidirectional=True))
        # c, d are isolated
        assert graph.get_connected_components() == 3

    def test_isolated_nodes(self) -> None:
        graph = StadiumGraph()
        a, b = _uid(), _uid()
        graph.add_node(GraphNode(entity_id=a, name="A", entity_type="gate", lat=40.0, lon=-74.0))
        graph.add_node(GraphNode(entity_id=b, name="B", entity_type="gate", lat=40.1, lon=-74.1))
        assert len(graph.get_isolated_nodes()) == 2

    def test_accessibility_filter(self) -> None:
        graph = StadiumGraph()
        a, b, c = _uid(), _uid(), _uid()

        for nid in [a, b, c]:
            graph.add_node(GraphNode(entity_id=nid, name="N", entity_type="gate", lat=40.0, lon=-74.0))

        # A -> B: wheelchair only
        graph.add_edge(GraphEdge(from_id=a, to_id=b, edge_type="walking",
                                 weight=100.0, accessibility_level="none", is_bidirectional=False))
        # A -> C: full accessibility
        graph.add_edge(GraphEdge(from_id=a, to_id=c, edge_type="walking",
                                 weight=200.0, accessibility_level="full", is_bidirectional=False))

        result = graph.find_shortest_path(a, c, accessibility_filter="full")
        assert result.path == [a, c]

    def test_edge_type_filter(self) -> None:
        graph = StadiumGraph()
        a, b, c = _uid(), _uid(), _uid()

        for nid in [a, b, c]:
            graph.add_node(GraphNode(entity_id=nid, name="N", entity_type="gate", lat=40.0, lon=-74.0))

        graph.add_edge(GraphEdge(from_id=a, to_id=b, edge_type="walking",
                                 weight=100.0, accessibility_level="full", is_bidirectional=False))
        graph.add_edge(GraphEdge(from_id=a, to_id=c, edge_type="emergency",
                                 weight=50.0, accessibility_level="full", is_bidirectional=False))

        result = graph.find_shortest_path(a, c, edge_type_filter="emergency")
        assert c in result.path
