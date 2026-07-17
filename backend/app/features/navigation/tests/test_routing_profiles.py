"""Tests for routing profiles, accessibility engine, and emergency routing."""

from __future__ import annotations

import uuid

import pytest

from app.features.navigation.accessibility.engine import AccessibilityEngine
from app.features.navigation.graph.graph_manager import NavigationGraph
from app.features.navigation.graph.models import NavEdge, NavNode, PathResult
from app.features.navigation.models.enums import (
    EmergencyType,
    RoutingProfile,
)
from app.features.navigation.routing.profile import (
    ProfileConfig,
    get_profile_config,
)


def _uid() -> uuid.UUID:
    return uuid.uuid4()


def _build_accessible_graph() -> NavigationGraph:
    graph = NavigationGraph()
    nodes = []
    for i in range(6):
        nid = _uid()
        nodes.append(nid)
        level = "none" if i == 3 else "full"
        graph.add_node(NavNode(
            node_id=nid, name=f"Node {i}",
            entity_type="corridor",
            lat=0.0, lon=float(i) * 0.0001,
            accessibility_level=level,
        ))
    edges = [
        (0, 1, "walking", 1.0),
        (1, 2, "walking", 1.0),
        (2, 3, "walking", 1.0),
        (3, 4, "walking", 1.0),
        (4, 5, "walking", 1.0),
        (0, 5, "elevator", 2.0),
    ]
    for from_i, to_i, etype, weight in edges:
        graph.add_edge(NavEdge(
            from_id=nodes[from_i], to_id=nodes[to_i],
            edge_type=etype, base_weight=weight,
            distance_meters=100.0,
        ))
    return graph


class TestRoutingProfiles:
    def test_all_profiles_have_weights(self) -> None:
        for profile in RoutingProfile:
            config = get_profile_config(profile)
            assert isinstance(config, ProfileConfig)
            assert len(config.objective_weights) > 0

    def test_wheelchair_requires_accessibility(self) -> None:
        config = get_profile_config(RoutingProfile.WHEELCHAIR_USER)
        assert config.requires_accessibility is True
        assert config.avoid_stairs is True
        assert config.avoid_escalators is True

    def test_volunteer_has_staff_access(self) -> None:
        config = get_profile_config(RoutingProfile.VOLUNTEER)
        assert config.prefer_staff_only is True
        assert "staff_only" in config.allowed_edge_types

    def test_invalid_profile_raises(self) -> None:
        from app.features.navigation.routing.profile import PROFILE_CONFIGS
        sentinel = uuid.uuid4()
        with pytest.raises(KeyError):
            PROFILE_CONFIGS[sentinel]


class TestAccessibilityEngine:
    def test_validate_accessible_route(self) -> None:
        graph = _build_accessible_graph()
        engine = AccessibilityEngine(graph)
        nodes = list(graph._nodes.keys())
        result = PathResult(
            path=[nodes[0], nodes[1], nodes[2], nodes[4], nodes[5]],
            edges=["walking", "walking", "walking", "walking"],
            total_distance_meters=400.0,
            total_time_seconds=4.0,
            total_cost=4.0,
        )
        valid, violations = engine.validate_route(result, RoutingProfile.WHEELCHAIR_USER)
        assert valid is True
        assert len(violations) == 0

    def test_validate_fails_for_inaccessible_node(self) -> None:
        graph = _build_accessible_graph()
        engine = AccessibilityEngine(graph)
        nodes = list(graph._nodes.keys())
        result = PathResult(
            path=[nodes[0], nodes[1], nodes[2], nodes[3], nodes[4], nodes[5]],
            edges=["walking", "walking", "walking", "walking", "walking"],
            total_distance_meters=500.0,
            total_time_seconds=5.0,
            total_cost=5.0,
        )
        valid, violations = engine.validate_route(result, RoutingProfile.WHEELCHAIR_USER)
        assert valid is False
        assert len(violations) > 0

    def test_non_accessible_profile_always_valid(self) -> None:
        graph = _build_accessible_graph()
        engine = AccessibilityEngine(graph)
        nodes = list(graph._nodes.keys())
        result = PathResult(
            path=[nodes[0], nodes[3], nodes[5]],
            edges=["walking", "walking"],
            total_distance_meters=200.0,
            total_time_seconds=2.0,
            total_cost=2.0,
        )
        valid, violations = engine.validate_route(result, RoutingProfile.SPECTATOR)
        assert valid is True


class TestEmergencyRouting:
    def test_emergency_destination_types_populated(self) -> None:
        from app.features.navigation.emergency.router import EMERGENCY_DESTINATION_TYPES
        for etype in EmergencyType:
            assert etype in EMERGENCY_DESTINATION_TYPES
            assert len(EMERGENCY_DESTINATION_TYPES[etype]) > 0
