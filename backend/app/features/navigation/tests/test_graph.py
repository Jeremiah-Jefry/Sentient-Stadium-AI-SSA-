"""Tests for the navigation graph manager and dynamic weights."""

from __future__ import annotations

import uuid

import pytest

from app.features.navigation.exceptions import (
    NodeNotFoundError,
)
from app.features.navigation.graph.dynamic_weights import (
    DynamicWeightEngine,
    IncidentState,
    InfrastructureState,
)
from app.features.navigation.graph.graph_manager import NavigationGraph
from app.features.navigation.graph.models import NavEdge, NavNode, WeightContext


def _uid() -> uuid.UUID:
    return uuid.uuid4()


def _build_linear_graph(n: int = 5) -> tuple[NavigationGraph, list[uuid.UUID]]:
    graph = NavigationGraph()
    nodes = []
    for _i in range(n):
        nid = _uid()
        nodes.append(nid)
        graph.add_node(NavNode(
            node_id=nid, name=f"Node {_i}",
            entity_type="corridor", lat=0.0, lon=float(_i) * 0.0001,
        ))
    for i in range(n - 1):
        graph.add_edge(NavEdge(
            from_id=nodes[i], to_id=nodes[i + 1],
            edge_type="walking", base_weight=1.0,
            distance_meters=100.0,
        ))
    return graph, nodes


class TestNavigationGraph:
    def test_add_node_and_retrieve(self) -> None:
        graph = NavigationGraph()
        nid = _uid()
        graph.add_node(NavNode(
            node_id=nid, name="Test",
            entity_type="gate", lat=0.0, lon=0.0,
        ))
        assert graph.get_node(nid) is not None
        assert graph.node_count == 1

    def test_add_bidirectional_edge(self) -> None:
        graph = NavigationGraph()
        a, b = _uid(), _uid()
        graph.add_node(NavNode(node_id=a, name="A", entity_type="corridor", lat=0, lon=0))
        graph.add_node(NavNode(node_id=b, name="B", entity_type="corridor", lat=0, lon=1))
        graph.add_edge(NavEdge(
            from_id=a, to_id=b, edge_type="walking",
            base_weight=1.0, is_bidirectional=True, distance_meters=100,
        ))
        assert len(graph.get_neighbors(a)) == 1
        assert len(graph.get_neighbors(b)) == 1
        assert graph.edge_count == 2

    def test_add_unidirectional_edge(self) -> None:
        graph = NavigationGraph()
        a, b = _uid(), _uid()
        graph.add_node(NavNode(node_id=a, name="A", entity_type="corridor", lat=0, lon=0))
        graph.add_node(NavNode(node_id=b, name="B", entity_type="corridor", lat=0, lon=1))
        graph.add_edge(NavEdge(
            from_id=a, to_id=b, edge_type="walking",
            base_weight=1.0, is_bidirectional=False, distance_meters=100,
        ))
        assert len(graph.get_neighbors(a)) == 1
        assert len(graph.get_neighbors(b)) == 0

    def test_find_shortest_path_linear(self) -> None:
        graph, nodes = _build_linear_graph(5)
        result = graph.find_shortest_path(nodes[0], nodes[4])
        assert result.path == nodes
        assert result.total_distance_meters == 400.0
        assert result.algorithm_used == "dijkstra"

    def test_node_not_found(self) -> None:
        graph, nodes = _build_linear_graph(3)
        with pytest.raises(NodeNotFoundError):
            graph.find_shortest_path(nodes[0], _uid())

    def test_remove_node(self) -> None:
        graph, nodes = _build_linear_graph(3)
        assert graph.remove_node(nodes[1])
        assert graph.get_node(nodes[1]) is None
        assert graph.node_count == 2

    def test_dynamic_weight_crowd(self) -> None:
        graph, nodes = _build_linear_graph(3)
        ctx = WeightContext(crowd_density=0.8)
        result = graph.find_shortest_path(nodes[0], nodes[2], ctx)
        assert result.total_cost > 2.0

    def test_dynamic_weight_emergency_blocks_staff(self) -> None:
        graph = NavigationGraph()
        a, b, c = _uid(), _uid(), _uid()
        for n in (a, b, c):
            graph.add_node(NavNode(
                node_id=n, name="N",
                entity_type="corridor", lat=0, lon=0,
            ))
        graph.add_edge(NavEdge(
            from_id=a, to_id=b, edge_type="walking",
            base_weight=1.0, distance_meters=10,
        ))
        graph.add_edge(NavEdge(
            from_id=b, to_id=c, edge_type="emergency",
            base_weight=1.0, distance_meters=10,
        ))
        ctx = WeightContext(emergency_active=True)
        result = graph.find_shortest_path(a, c, ctx)
        assert "emergency" in result.edges

    def test_node_update(self) -> None:
        graph = NavigationGraph()
        nid = _uid()
        graph.add_node(NavNode(node_id=nid, name="V1", entity_type="gate", lat=0, lon=0))
        graph.update_node(NavNode(node_id=nid, name="V2", entity_type="gate", lat=0, lon=0))
        assert graph.get_node(nid).name == "V2"

    def test_find_nearest(self) -> None:
        graph, nodes = _build_linear_graph(5)
        aed_id = _uid()
        graph.add_node(NavNode(
            node_id=aed_id, name="AED", entity_type="aed",
            lat=0.0, lon=0.0002,
        ))
        graph.add_edge(NavEdge(
            from_id=nodes[2], to_id=aed_id,
            edge_type="walking", base_weight=1.0,
            distance_meters=50.0,
        ))
        result = graph.find_nearest(nodes[0], {"aed"})
        assert result is not None

    def test_find_within_radius(self) -> None:
        graph, nodes = _build_linear_graph(5)
        results = graph.find_within_radius(nodes[0], 300.0)
        assert len(results) >= 2


class TestDynamicWeightEngine:
    def test_update_crowd_density(self) -> None:
        engine = DynamicWeightEngine()
        engine.update_crowd_density("zone-1", 0.8)
        ctx = engine.build_context("zone-1")
        assert ctx.crowd_density == 0.8

    def test_update_weather(self) -> None:
        engine = DynamicWeightEngine()
        engine.update_weather(rain=60.0)
        ctx = engine.build_context()
        assert ctx.weather_penalty > 0

    def test_add_incident(self) -> None:
        engine = DynamicWeightEngine()
        engine.add_incident(IncidentState(
            incident_type="medical", severity=3.0, zone_id="z1",
        ))
        ctx = engine.build_context("z1")
        assert ctx.medical_incident_nearby is True

    def test_emergency_incident(self) -> None:
        engine = DynamicWeightEngine()
        engine.add_incident(IncidentState(
            incident_type="fire", severity=5.0, zone_id="z1",
        ))
        ctx = engine.build_context("z1")
        assert ctx.emergency_active is True

    def test_remove_incident(self) -> None:
        engine = DynamicWeightEngine()
        engine.add_incident(IncidentState(
            incident_type="medical", severity=1.0, zone_id="z1",
        ))
        engine.remove_incident("medical", "z1")
        ctx = engine.build_context("z1")
        assert ctx.medical_incident_nearby is False

    def test_infrastructure_update(self) -> None:
        engine = DynamicWeightEngine()
        engine.update_infrastructure(InfrastructureState(
            escalator_status={"esc-1": False},
        ))
        ctx = engine.build_context()
        assert ctx.maintenance_active is True

    def test_snapshot(self) -> None:
        engine = DynamicWeightEngine()
        engine.update_crowd_density("z1", 0.5)
        snap = engine.snapshot()
        assert snap["crowd_zones"] == 1
