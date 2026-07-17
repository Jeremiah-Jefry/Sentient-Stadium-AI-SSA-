"""Tests for explanation generation."""
from __future__ import annotations

from app.features.ai_intelligence.explainability.explainability_engine import (
    ExplainabilityEngine,
    Explanation,
)


class TestExplainabilityEngine:
    """Tests for the ExplainabilityEngine."""

    def setup_method(self) -> None:
        self.engine = ExplainabilityEngine()

    def test_explain_risk_has_reason(self) -> None:
        """Risk explanation should include a reason string."""
        assessment = {
            "risk_level": "red",
            "risk_score": 0.82,
            "risk_factors": {"density": 0.9, "flow": 0.7, "weather": 0.1},
            "contributing_events": ["evt-1"],
        }
        explanation = self.engine.explain_risk(assessment, [], {})
        assert isinstance(explanation, Explanation)
        assert len(explanation.reason) > 0

    def test_explain_risk_has_evidence(self) -> None:
        """Risk explanation should cite evidence events."""
        events = [
            {
                "id": "evt-1", "type": "crowd_surge",
                "description": "High density at gate A", "severity": 4,
            },
            {"id": "evt-2", "type": "medical", "description": "Minor injury", "severity": 2},
        ]
        assessment = {
            "risk_level": "orange",
            "risk_score": 0.6,
            "risk_factors": {"density": 0.8, "medical": 0.4},
            "contributing_events": ["evt-1"],
        }
        explanation = self.engine.explain_risk(assessment, events, {})
        assert len(explanation.evidence) > 0
        evidence_ids = [e["event_id"] for e in explanation.evidence]
        assert "evt-1" in evidence_ids

    def test_explain_risk_summary(self) -> None:
        """Risk explanation should include a summary."""
        assessment = {
            "risk_level": "yellow",
            "risk_score": 0.35,
            "risk_factors": {"density": 0.4, "flow": 0.3},
            "contributing_events": [],
        }
        explanation = self.engine.explain_risk(assessment, [], {})
        assert "yellow" in explanation.summary.lower()
        assert "0.35" in explanation.summary or "35%" in explanation.summary

    def test_explain_risk_ranked_factors(self) -> None:
        """Risk explanation should rank factors by contribution."""
        assessment = {
            "risk_level": "red",
            "risk_score": 0.8,
            "risk_factors": {"density": 0.95, "flow": 0.3, "weather": 0.1, "medical": 0.5},
            "contributing_events": [],
        }
        explanation = self.engine.explain_risk(assessment, [], {})
        factor_keys = [f["factor"] for f in explanation.contributing_factors]
        assert factor_keys[0] == "density"

    def test_explain_prediction_has_confidence(self) -> None:
        """Prediction explanation should include confidence."""
        prediction = {
            "prediction_type": "bottleneck",
            "predicted_value": 0.75,
            "confidence": 0.85,
            "contributing_factors": [{"name": "source_zone", "value": "A"}],
            "evidence_count": 12,
        }
        explanation = self.engine.explain_prediction(prediction, [], {})
        assert explanation.confidence == 0.85

    def test_explain_prediction_summary(self) -> None:
        """Prediction explanation should describe the prediction."""
        prediction = {
            "prediction_type": "queue_growth",
            "predicted_value": 0.6,
            "confidence": 0.7,
            "contributing_factors": [],
            "evidence_count": 5,
        }
        explanation = self.engine.explain_prediction(prediction, [], {})
        assert "queue_growth" in explanation.summary.lower()

    def test_explain_decision_has_alternatives(self) -> None:
        """Decision explanation should list alternatives considered."""
        decision = {
            "intervention_type": "redirect_volunteers",
            "confidence": 0.75,
            "reasoning": {"evidence": [], "factors": []},
            "expected_outcome": {"risk_reduction": 0.22, "description": "Reduced crowd pressure"},
        }
        alternatives = [
            {"intervention_type": "do_nothing", "confidence": 1.0},
            {"intervention_type": "open_secondary_gate", "confidence": 0.65},
        ]
        explanation = self.engine.explain_decision(decision, alternatives, {})
        assert len(explanation.alternatives_considered) > 0

    def test_explain_decision_has_tradeoffs(self) -> None:
        """Decision explanation should describe tradeoffs."""
        decision = {
            "intervention_type": "deploy_medical",
            "confidence": 0.80,
            "reasoning": {},
            "expected_outcome": {"risk_reduction": 0.38, "speed": "fast"},
        }
        alternatives = []
        explanation = self.engine.explain_decision(decision, alternatives, {})
        assert len(explanation.tradeoffs) > 0
        aspects = [t["aspect"] for t in explanation.tradeoffs]
        assert "risk_reduction" in aspects

    def test_volunteer_briefing_concise(self) -> None:
        """Volunteer briefing should be under 280 characters."""
        explanation = Explanation(
            summary="Risk is yellow due to high density at Gate A.",
            reason="Density is above 80% capacity.",
            contributing_factors=[{"factor": "density"}],
            confidence=0.65,
            expected_outcome="Monitor closely.",
        )
        briefing = self.engine.format_volunteer_briefing(explanation)
        assert len(briefing) <= 280, (
            f"Briefing too long ({len(briefing)} chars): {briefing}"
        )

    def test_volunteer_briefing_contains_confidence(self) -> None:
        """Volunteer briefing should include confidence percentage."""
        explanation = Explanation(
            summary="Risk is red.",
            reason="Multiple factors.",
            confidence=0.85,
        )
        briefing = self.engine.format_volunteer_briefing(explanation)
        assert "85%" in briefing

    def test_evidence_limited(self) -> None:
        """Evidence should be limited to MAX_EVIDENCE items."""
        events = [{"id": f"evt-{i}", "type": "test", "severity": 1} for i in range(20)]
        assessment = {
            "risk_level": "red",
            "risk_score": 0.8,
            "risk_factors": {"density": 0.9},
            "contributing_events": [f"evt-{i}" for i in range(20)],
        }
        explanation = self.engine.explain_risk(assessment, events, {})
        assert len(explanation.evidence) <= 10

    def test_no_factors(self) -> None:
        """Explanation should handle empty risk factors."""
        assessment = {
            "risk_level": "green",
            "risk_score": 0.0,
            "risk_factors": {},
            "contributing_events": [],
        }
        explanation = self.engine.explain_risk(assessment, [], {})
        assert len(explanation.reason) > 0
