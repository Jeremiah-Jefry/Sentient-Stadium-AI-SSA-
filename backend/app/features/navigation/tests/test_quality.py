"""Tests for route quality engine, replanner, and explainability."""

from __future__ import annotations

import uuid

from app.features.navigation.explainability.explainer import RouteExplainer
from app.features.navigation.graph.graph_manager import NavigationGraph
from app.features.navigation.graph.models import NavEdge, NavNode, PathResult, WeightContext
from app.features.navigation.models.enums import ReplanTrigger, RoutingProfile
from app.features.navigation.pathfinding.algorithm import AlgorithmRegistry
from app.features.navigation.routing.quality import RouteQualityEngine
from app.features.navigation.routing.replanner import RouteReplanner
from app.features.navigation.simulation.simulator import RouteSimulator


def _uid() -> uuid.UUID:
    return uuid.uuid4()


def _build_graph() -> tuple[NavigationGraph, list[uuid.UUID]]:
    graph = NavigationGraph()
    nodes = []
    for i in range(5):
        nid = _uid()
        nodes.append(nid)
        graph.add_node(NavNode(
            node_id=nid, name=f"Node {i}",
            entity_type="corridor",
            lat=0.0, lon=float(i) * 0.0001,
            current_capacity=i * 20,
            max_capacity=100,
        ))
    for i in range(4):
        graph.add_edge(NavEdge(
            from_id=nodes[i], to_id=nodes[i + 1],
            edge_type="walking", base_weight=1.0,
            distance_meters=100.0,
        ))
    return graph, nodes


class TestRouteQualityEngine:
    def test_assess_green_route(self) -> None:
        graph, nodes = _build_graph()
        engine = RouteQualityEngine(graph)
        result = PathResult(
            path=nodes, edges=["walking"] * 4,
            total_distance_meters=400.0, total_time_seconds=60.0,
            total_cost=4.0, confidence=1.0,
        )
        metrics = engine.assess(result, RoutingProfile.SPECTATOR)
        assert metrics.grade in ("A+", "A", "A-", "B+", "B")
        assert 0 <= metrics.overall_score <= 1.0

    def test_assess_with_high_risk(self) -> None:
        graph, nodes = _build_graph()
        engine = RouteQualityEngine(graph)
        result = PathResult(
            path=nodes, edges=["walking"] * 4,
            total_distance_meters=400.0, total_time_seconds=60.0,
            total_cost=4.0,
        )
        ctx = WeightContext(risk_score=0.9)
        metrics = engine.assess(result, RoutingProfile.SPECTATOR, ctx)
        assert metrics.safety_score < 0.7

    def test_grade_bounds(self) -> None:
        assert RouteQualityEngine._score_to_grade(1.0) == "A+"
        assert RouteQualityEngine._score_to_grade(0.0) == "F"
        assert RouteQualityEngine._score_to_grade(0.5) in ("C", "C-")


class TestReplanner:
    def test_register_and_unregister(self) -> None:
        graph, nodes = _build_graph()
        reg = AlgorithmRegistry()
        replanner = RouteReplanner(graph, reg)
        route = PathResult(
            path=nodes[:3], edges=["walking", "walking"],
            total_distance_meters=200.0, total_time_seconds=20.0,
            total_cost=2.0,
        )
        replanner.register_route("r1", "u1", RoutingProfile.SPECTATOR, nodes[0], nodes[2], route)
        assert replanner.active_count == 1
        replanner.unregister_route("r1")
        assert replanner.active_count == 0

    def test_handle_trigger_no_match(self) -> None:
        graph, nodes = _build_graph()
        reg = AlgorithmRegistry()
        replanner = RouteReplanner(graph, reg)
        route = PathResult(
            path=nodes[:3], edges=["walking", "walking"],
            total_distance_meters=200.0, total_time_seconds=20.0,
            total_cost=2.0,
        )
        replanner.register_route("r1", "u1", RoutingProfile.SPECTATOR, nodes[0], nodes[2], route)
        results = replanner.handle_trigger(ReplanTrigger.GATE_CLOSURE, "unknown_zone")
        assert len(results) == 0


class TestExplainer:
    def test_explain_generates_summary(self) -> None:
        graph, nodes = _build_graph()
        explainer = RouteExplainer(graph)
        result = PathResult(
            path=nodes, edges=["walking"] * 4,
            total_distance_meters=400.0, total_time_seconds=60.0,
            total_cost=4.0, confidence=1.0,
        )
        from app.features.navigation.routing.quality import RouteQualityEngine
        quality = RouteQualityEngine(graph)
        metrics = quality.assess(result, RoutingProfile.SPECTATOR)
        explanation = explainer.explain(result, metrics, RoutingProfile.SPECTATOR)
        assert len(explanation.summary) > 0
        assert len(explanation.why_selected) > 0


class TestSimulator:
    def test_simulate_clean_route(self) -> None:
        graph, nodes = _build_graph()
        sim = RouteSimulator(graph)
        result = PathResult(
            path=nodes, edges=["walking"] * 4,
            total_distance_meters=400.0, total_time_seconds=60.0,
            total_cost=4.0, confidence=1.0,
        )
        sim_result = sim.simulate(result)
        assert 0 <= sim_result.success_probability <= 1.0

    def test_compare_routes(self) -> None:
        graph, nodes = _build_graph()
        sim = RouteSimulator(graph)
        route1 = PathResult(
            path=nodes[:3], edges=["walking", "walking"],
            total_distance_meters=200.0, total_time_seconds=30.0,
            total_cost=2.0,
        )
        route2 = PathResult(
            path=nodes, edges=["walking"] * 4,
            total_distance_meters=400.0, total_time_seconds=60.0,
            total_cost=4.0,
        )
        ranked = sim.compare_routes([route1, route2])
        assert len(ranked) == 2
        assert ranked[0][1].success_probability >= ranked[1][1].success_probability
