"""Tests for spatial reasoning."""
from __future__ import annotations

from app.features.ai_intelligence.context.spatial_reasoning import (
    RISK_PROPAGATION_DECAY,
    SpatialReasoner,
)


class TestSpatialReasoner:
    """Tests for the SpatialReasoner."""

    def test_compute_zone_risk_empty(self) -> None:
        """Empty zone should have low risk."""
        reasoner = SpatialReasoner()
        risk = reasoner.compute_zone_risk("zone-a", {
            "capacity": 1000,
            "occupancy": 0,
            "incidents": [],
            "blocked_exits": 0,
            "total_exits": 4,
        })
        assert risk == 0.0, f"Empty zone should have 0 risk, got {risk}"

    def test_compute_zone_risk_high_occupancy(self) -> None:
        """High occupancy should yield high risk."""
        reasoner = SpatialReasoner()
        risk = reasoner.compute_zone_risk("zone-a", {
            "capacity": 100,
            "occupancy": 100,
            "incidents": [],
            "blocked_exits": 0,
            "total_exits": 4,
        })
        assert risk > 0.4, f"High occupancy should yield significant risk, got {risk}"

    def test_compute_zone_risk_zero_capacity(self) -> None:
        """Zero capacity should return 1.0."""
        reasoner = SpatialReasoner()
        risk = reasoner.compute_zone_risk("zone-a", {"capacity": 0, "occupancy": 0})
        assert risk == 1.0

    def test_neighbor_influence_propagation(self) -> None:
        """High-risk neighbors should increase zone risk."""
        zone_graph = {
            "A": {"neighbors": ["B"]},
            "B": {"neighbors": []},
        }
        reasoner = SpatialReasoner(zone_graph)
        reasoner._risk_cache["B"] = 0.9
        influence = reasoner.compute_neighbor_influence("A")
        expected = 0.9 * RISK_PROPAGATION_DECAY
        assert abs(influence - expected) < 0.01, (
            f"Expected influence ~{expected}, got {influence}"
        )

    def test_neighbor_no_neighbors(self) -> None:
        """Zone with no neighbors should have 0 influence."""
        reasoner = SpatialReasoner({"A": {"neighbors": []}})
        influence = reasoner.compute_neighbor_influence("A")
        assert influence == 0.0

    def test_find_bottlenecks(self) -> None:
        """Should identify zones with high in-flow and limited capacity."""
        zone_graph = {
            "gate-a": {"neighbors": ["concourse"]},
            "concourse": {"neighbors": ["gate-a"]},
        }
        reasoner = SpatialReasoner(zone_graph)
        venue_data = {
            "gate-a": {
                "capacity": 100,
                "occupancy": 90,
                "incidents": [],
                "blocked_exits": 0,
                "total_exits": 2,
            },
            "concourse": {
                "capacity": 500,
                "occupancy": 100,
                "incidents": [],
                "blocked_exits": 0,
                "total_exits": 4,
            },
        }
        bottlenecks = reasoner.find_bottlenecks(venue_data)
        assert len(bottlenecks) >= 1
        assert bottlenecks[0]["zone_id"] == "gate-a"

    def test_congestion_spread_decay(self) -> None:
        """Congestion should decay with distance from source."""
        zone_graph = {
            "A": {"neighbors": ["B"]},
            "B": {"neighbors": ["C"]},
            "C": {"neighbors": []},
        }
        reasoner = SpatialReasoner(zone_graph)
        spread = reasoner.predict_congestion_spread("A", 1.0, 3)
        assert len(spread) == 2
        b_impact = spread[0]["predicted_intensity"]
        c_impact = spread[1]["predicted_intensity"]
        assert b_impact > c_impact, "Impact should decay with depth"
        assert abs(b_impact - RISK_PROPAGATION_DECAY) < 0.01

    def test_congestion_spread_max_steps(self) -> None:
        """Spread should respect max steps limit."""
        zone_graph = {
            "A": {"neighbors": ["B"]},
            "B": {"neighbors": ["C"]},
            "C": {"neighbors": ["D"]},
            "D": {"neighbors": []},
        }
        reasoner = SpatialReasoner(zone_graph)
        spread = reasoner.predict_congestion_spread("A", 1.0, 1)
        assert len(spread) == 1
        assert spread[0]["zone_id"] == "B"

    def test_evacuation_efficiency_full_exits(self) -> None:
        """Zone with all exits open should have high efficiency."""
        reasoner = SpatialReasoner({
            "zone-a": {"exit_count": 4, "capacity": 1000, "blocked_exits": 0},
        })
        efficiency = reasoner.get_evacuation_efficiency("zone-a")
        assert efficiency > 0.5, f"Expected high evacuation efficiency, got {efficiency}"

    def test_evacuation_efficiency_blocked_exits(self) -> None:
        """Blocked exits should reduce evacuation efficiency."""
        reasoner = SpatialReasoner({
            "zone-a": {"exit_count": 4, "capacity": 1000, "blocked_exits": 3},
        })
        efficiency = reasoner.get_evacuation_efficiency("zone-a")
        full_efficiency = reasoner.get_evacuation_efficiency("zone-a")
        reasoner2 = SpatialReasoner({
            "zone-a": {"exit_count": 4, "capacity": 1000, "blocked_exits": 0},
        })
        full_eff = reasoner2.get_evacuation_efficiency("zone-a")
        assert efficiency < full_eff

    def test_evacuation_efficiency_no_exits(self) -> None:
        """Zone with no exits should have 0 efficiency."""
        reasoner = SpatialReasoner({
            "zone-a": {"exit_count": 0, "capacity": 1000, "blocked_exits": 0},
        })
        efficiency = reasoner.get_evacuation_efficiency("zone-a")
        assert efficiency == 0.0

    def test_compute_route_impact_same_zone(self) -> None:
        """Route from zone to itself should have 0 impact."""
        reasoner = SpatialReasoner({"A": {"neighbors": ["B"]}})
        result = reasoner.compute_route_impact("A", "A")
        assert result["impact_score"] == 0.0
        assert result["hops"] == 0
        assert result["route"] == ["A"]

    def test_compute_route_impact_path(self) -> None:
        """Route impact should reflect risk along path."""
        zone_graph = {
            "A": {"neighbors": ["B"]},
            "B": {"neighbors": ["C"]},
            "C": {"neighbors": []},
        }
        reasoner = SpatialReasoner(zone_graph)
        reasoner._risk_cache["A"] = 0.0
        reasoner._risk_cache["B"] = 0.8
        reasoner._risk_cache["C"] = 0.0
        result = reasoner.compute_route_impact("A", "C")
        assert result["hops"] == 2
        assert result["impact_score"] > 0.0

    def test_compute_route_impact_unreachable(self) -> None:
        """Unreachable destination should return impact 1.0."""
        reasoner = SpatialReasoner({"A": {"neighbors": []}})
        result = reasoner.compute_route_impact("A", "B")
        assert result["impact_score"] == 1.0
        assert result["hops"] == -1
        assert result["route"] == []

    def test_bottleneck_severity_classification(self) -> None:
        """Severity should increase with occupancy ratio."""
        from app.features.ai_intelligence.context.spatial_reasoning import (
            SpatialReasoner,
        )
        ratios = [0.7, 0.8, 0.9, 1.0]
        severities = [SpatialReasoner._classify_bottleneck_severity(r) for r in ratios]
        for i in range(1, len(severities)):
            assert severities[i] >= severities[i - 1]

    def test_bottleneck_cause_identification(self) -> None:
        """Should identify bottleneck cause from zone data."""
        from app.features.ai_intelligence.context.spatial_reasoning import (
            SpatialReasoner,
        )
        cause_blocked = SpatialReasoner._identify_bottleneck_cause(
            {"blocked_exits": 2, "incidents": []}
        )
        assert "blocked_exits" in cause_blocked

        cause_incidents = SpatialReasoner._identify_bottleneck_cause(
            {"blocked_exits": 0, "incidents": [{"type": "fight"}]}
        )
        assert "incidents" in cause_incidents

        cause_occupancy = SpatialReasoner._identify_bottleneck_cause({})
        assert cause_occupancy == "high_occupancy"
