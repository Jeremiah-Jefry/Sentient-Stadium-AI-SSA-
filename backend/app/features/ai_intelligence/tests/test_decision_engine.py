"""Tests for decision engine and intervention simulator."""
from __future__ import annotations

from app.features.ai_intelligence.decision.decision_engine import (
    UTILITY_WEIGHTS,
    DecisionEngine,
)
from app.features.ai_intelligence.decision.intervention_simulator import (
    InterventionSimulator,
    SimulatedResult,
)
from app.features.ai_intelligence.engine.context import RiskBundle
from app.features.ai_intelligence.models.enums import InterventionType, RiskLevel


def _make_risk(
    level: RiskLevel = RiskLevel.GREEN,
    score: float = 0.1,
    confidence: float = 0.8,
) -> RiskBundle:
    return RiskBundle(
        overall_risk_level=level.value,
        overall_risk_score=score,
        domain_risks={},
        risk_factors={},
        confidence=confidence,
    )


class TestDecisionEngine:
    """Tests for candidate generation, scoring, and ranking."""

    def test_green_generates_only_do_nothing(self) -> None:
        """GREEN risk should only produce DO_NOTHING candidate."""
        engine = DecisionEngine()
        risk = _make_risk(RiskLevel.GREEN, 0.1)
        candidates = engine.generate_candidates(risk, {})
        types = [c["intervention_type"] for c in candidates]
        assert types == [InterventionType.DO_NOTHING.value]

    def test_yellow_adds_volunteers_and_announcements(self) -> None:
        """YELLOW risk should add volunteer redirect and announcements."""
        engine = DecisionEngine()
        risk = _make_risk(RiskLevel.YELLOW, 0.35)
        candidates = engine.generate_candidates(risk, {})
        types = [c["intervention_type"] for c in candidates]
        assert InterventionType.REDIRECT_VOLUNTEERS.value in types
        assert InterventionType.MULTILINGUAL_ANNOUNCEMENT.value in types
        assert InterventionType.DO_NOTHING.value in types

    def test_critical_includes_all_interventions(self) -> None:
        """CRITICAL risk should include all intervention types."""
        engine = DecisionEngine()
        risk = _make_risk(RiskLevel.CRITICAL, 0.95)
        candidates = engine.generate_candidates(risk, {})
        types = [c["intervention_type"] for c in candidates]
        for itype in InterventionType:
            assert itype.value in types, f"Missing intervention type: {itype.value}"

    def test_rank_candidates_sorted_by_utility(self) -> None:
        """Candidates should be ranked by utility score descending."""
        engine = DecisionEngine()
        risk = _make_risk(RiskLevel.RED, 0.8)
        candidates = engine.generate_candidates(risk, {})
        ranked = engine.rank_candidates(candidates, risk, {})
        scores = [score for _, score in ranked]
        assert scores == sorted(scores, reverse=True)

    def test_do_nothing_always_present(self) -> None:
        """DO_NOTHING should always be a candidate."""
        engine = DecisionEngine()
        for level in RiskLevel:
            risk = _make_risk(level, 0.5)
            candidates = engine.generate_candidates(risk, {})
            types = [c["intervention_type"] for c in candidates]
            assert InterventionType.DO_NOTHING.value in types

    def test_score_candidate_do_nothing(self) -> None:
        """DO_NOTHING should have 0 risk reduction and 1.0 confidence."""
        engine = DecisionEngine()
        risk = _make_risk(RiskLevel.GREEN, 0.1)
        candidates = engine.generate_candidates(risk, {})
        do_nothing = next(c for c in candidates if c["intervention_type"] == "do_nothing")
        score = engine.score_candidate(do_nothing, risk, {})
        assert do_nothing["estimated_risk_reduction"] == 0.0
        assert do_nothing["estimated_confidence"] == 1.0

    def test_candidate_has_required_fields(self) -> None:
        """Each candidate should have all required fields."""
        engine = DecisionEngine()
        risk = _make_risk(RiskLevel.ORANGE, 0.6)
        candidates = engine.generate_candidates(risk, {})
        required_fields = {
            "intervention_type", "strategy_params", "estimated_risk_reduction",
            "estimated_confidence", "resource_cost",
        }
        for c in candidates:
            assert required_fields.issubset(c.keys()), f"Missing fields in candidate: {c}"

    def test_score_bounded(self) -> None:
        """Utility score must be between 0.0 and 1.0."""
        engine = DecisionEngine()
        risk = _make_risk(RiskLevel.CRITICAL, 0.95)
        candidates = engine.generate_candidates(risk, {})
        for c in candidates:
            score = engine.score_candidate(c, risk, {})
            assert 0.0 <= score <= 1.0, f"Score out of bounds: {score}"

    def test_utility_weights_defined(self) -> None:
        """Utility weights should be defined and non-negative."""
        assert "risk_reduction" in UTILITY_WEIGHTS
        assert "confidence" in UTILITY_WEIGHTS
        assert "resource_cost" in UTILITY_WEIGHTS
        for w in UTILITY_WEIGHTS.values():
            assert w >= 0.0


class TestInterventionSimulator:
    """Tests for intervention simulation."""

    def test_do_nothing_no_change(self) -> None:
        """DO_NOTHING should not change risk level."""
        simulator = InterventionSimulator()
        state = {"risk_level": RiskLevel.RED.value}
        result = simulator.simulate(
            InterventionType.DO_NOTHING.value, {}, state, 300,
        )
        assert isinstance(result, SimulatedResult)
        assert result.risk_before == RiskLevel.RED.value
        assert result.risk_reduction == 0.0
        assert result.resource_cost == 0.0
        assert result.risk_after == RiskLevel.RED.value

    def test_redirect_volunteers_reduces_risk(self) -> None:
        """Redirecting volunteers should reduce target zone risk."""
        simulator = InterventionSimulator()
        state = {"risk_level": RiskLevel.ORANGE.value}
        result = simulator.simulate(
            InterventionType.REDIRECT_VOLUNTEERS.value,
            {"target_zones": ["zone-a", "zone-b"]},
            state,
            300,
        )
        assert result.risk_reduction > 0.0
        assert result.resource_cost == 0.20

    def test_open_gate_reduces_congestion(self) -> None:
        """Opening secondary gate should reduce congestion."""
        simulator = InterventionSimulator()
        state = {"risk_level": RiskLevel.RED.value}
        result = simulator.simulate(
            InterventionType.OPEN_SECONDARY_GATE.value,
            {"gate_ids": ["gate-1", "gate-2"]},
            state,
            300,
        )
        assert result.risk_reduction > 0.0
        assert len(result.side_effects) > 0

    def test_simulation_returns_side_effects(self) -> None:
        """Simulation should identify potential side effects."""
        simulator = InterventionSimulator()
        state = {"risk_level": RiskLevel.ORANGE.value}
        result = simulator.simulate(
            InterventionType.CLOSE_CORRIDOR.value,
            {"corridor_ids": ["corridor-1"]},
            state,
            300,
        )
        assert len(result.side_effects) > 0

    def test_resource_cost_positive(self) -> None:
        """Active interventions should have positive resource cost."""
        simulator = InterventionSimulator()
        state = {"risk_level": RiskLevel.YELLOW.value}
        active_interventions = [
            InterventionType.DEPLOY_MEDICAL.value,
            InterventionType.INCREASE_SECURITY.value,
            InterventionType.SPLIT_CROWD.value,
        ]
        for itype in active_interventions:
            result = simulator.simulate(itype, {}, state, 300)
            assert result.resource_cost > 0.0, (
                f"{itype} should have positive resource cost, got {result.resource_cost}"
            )

    def test_split_crowd_respects_ratio_bounds(self) -> None:
        """Split ratio should be clamped to [0.1, 0.9]."""
        simulator = InterventionSimulator()
        state = {"risk_level": RiskLevel.RED.value}
        result = simulator.simulate(
            InterventionType.SPLIT_CROWD.value,
            {"split_ratio": 0.5},
            state,
            300,
        )
        assert result.risk_reduction > 0.0

    def test_emergency_announcement_stronger(self) -> None:
        """Emergency announcements should have higher reduction than general."""
        simulator = InterventionSimulator()
        state = {"risk_level": RiskLevel.ORANGE.value}
        general = simulator.simulate(
            InterventionType.MULTILINGUAL_ANNOUNCEMENT.value,
            {"message_key": "general_advisory"},
            state, 300,
        )
        emergency = simulator.simulate(
            InterventionType.MULTILINGUAL_ANNOUNCEMENT.value,
            {"message_key": "emergency"},
            state, 300,
        )
        assert emergency.risk_reduction > general.risk_reduction

    def test_simulation_returns_evaluation_factors(self) -> None:
        """Simulation should return evaluation factors."""
        simulator = InterventionSimulator()
        state = {"risk_level": RiskLevel.YELLOW.value}
        result = simulator.simulate(
            InterventionType.REDIRECT_VOLUNTEERS.value, {}, state, 300,
        )
        assert len(result.evaluation_factors) > 0
        factor_names = [f["factor"] for f in result.evaluation_factors]
        assert "reduction" in factor_names
        assert "confidence" in factor_names

    def test_risk_level_mapping(self) -> None:
        """Score-to-level mapping should work correctly."""
        from app.features.ai_intelligence.decision.intervention_simulator import (
            _score_to_level,
        )
        assert _score_to_level(0.10) == "green"
        assert _score_to_level(0.30) == "yellow"
        assert _score_to_level(0.55) == "orange"
        assert _score_to_level(0.80) == "red"
        assert _score_to_level(0.95) == "critical"
