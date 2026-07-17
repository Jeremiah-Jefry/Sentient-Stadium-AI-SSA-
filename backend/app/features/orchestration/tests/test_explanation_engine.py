"""Tests for ExplanationEngine — role-based explanations for volunteers, admins, and emergency leads."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.features.orchestration.explanation.explanation_engine import ExplanationEngine
from app.features.orchestration.explanation.types import (
    ConfidenceReport,
    ReasoningChain,
    SafetyReport,
)
from app.features.orchestration.models.enums import UserRole
from app.shared.result import Success


@pytest.fixture
def engine() -> ExplanationEngine:
    return ExplanationEngine()


def _base_recommendation() -> dict:
    return {
        "recommendation": "Open overflow gate B3 to relieve crowd pressure",
        "confidence": 0.85,
        "agents_used": [
            {"agent_id": str(uuid4()), "agent_name": "Crowd Intelligence Agent"},
            {"agent_id": str(uuid4()), "agent_name": "Navigation Agent"},
        ],
        "reasoning": {"strategy": "proactive_crowd_management"},
    }


def _base_chain() -> ReasoningChain:
    return ReasoningChain(
        stages=[
            {"name": "observe", "confidence": 0.8, "output": {}},
            {"name": "think", "confidence": 0.75, "output": {}},
            {"name": "plan", "confidence": 0.82, "output": {}},
        ],
        final_reasoning="Evidence-based crowd management plan",
        stage_count=3,
        duration_ms=45.0,
    )


def _base_confidence() -> ConfidenceReport:
    return ConfidenceReport(
        overall=0.85,
        per_agent={},
        evidence_quality=0.8,
        data_freshness=0.9,
        reasoning="High confidence from multiple sources",
    )


def _base_safety() -> SafetyReport:
    return SafetyReport(
        safety_level="safe",
        violations=[],
        warnings=[],
        requires_human_review=False,
    )


class TestExplanationEngine:

    @pytest.mark.asyncio
    async def test_explain_volunteer(self, engine: ExplanationEngine) -> None:
        agent_id = uuid4()
        result = await engine.explain(
            recommendation=_base_recommendation(),
            reasoning_chain=_base_chain(),
            agent_outputs={agent_id: {"confidence": 0.85, "evidence": [], "agent_name": "Crowd Agent"}},
            confidence_report=_base_confidence(),
            safety_report=_base_safety(),
            user_role=UserRole.VOLUNTEER,
            context={},
        )
        assert isinstance(result, Success)
        explanation = result.value
        assert explanation.depth_level == "simple"
        assert "Recommended action" in explanation.decision_summary
        assert "analyzed available information" in explanation.reasoning_summary.lower()
        assert explanation.role_adjusted is True

    @pytest.mark.asyncio
    async def test_explain_admin(self, engine: ExplanationEngine) -> None:
        agent_id = uuid4()
        result = await engine.explain(
            recommendation=_base_recommendation(),
            reasoning_chain=_base_chain(),
            agent_outputs={agent_id: {"confidence": 0.85, "evidence": [{"type": "sensor"}], "agent_name": "Crowd Agent"}},
            confidence_report=_base_confidence(),
            safety_report=_base_safety(),
            user_role=UserRole.ADMIN,
            context={},
        )
        assert isinstance(result, Success)
        explanation = result.value
        assert explanation.depth_level == "detailed"
        assert "Confidence" in explanation.decision_summary
        assert explanation.role_adjusted is False

    @pytest.mark.asyncio
    async def test_explain_emergency_lead(self, engine: ExplanationEngine) -> None:
        agent_id = uuid4()
        result = await engine.explain(
            recommendation=_base_recommendation(),
            reasoning_chain=_base_chain(),
            agent_outputs={agent_id: {"confidence": 0.85, "evidence": [], "agent_name": "Medical Agent"}},
            confidence_report=_base_confidence(),
            safety_report=_base_safety(),
            user_role=UserRole.EMERGENCY_LEAD,
            context={},
        )
        assert isinstance(result, Success)
        explanation = result.value
        assert explanation.depth_level == "detailed"
        assert len(explanation.tradeoffs) >= 1

    @pytest.mark.asyncio
    async def test_emergency_lead_safety_urgency(self, engine: ExplanationEngine) -> None:
        agent_id = uuid4()
        dangerous_safety = SafetyReport(
            safety_level="critical",
            violations=[{"severity": "critical", "rule": "SR-007"}],
            warnings=["Evacuation priority"],
            requires_human_review=True,
        )
        result = await engine.explain(
            recommendation=_base_recommendation(),
            reasoning_chain=_base_chain(),
            agent_outputs={agent_id: {"confidence": 0.85, "evidence": [], "agent_name": "Crowd Agent"}},
            confidence_report=_base_confidence(),
            safety_report=dangerous_safety,
            user_role=UserRole.EMERGENCY_LEAD,
            context={},
        )
        assert isinstance(result, Success)
        explanation = result.value
        assert "SAFETY ALERT" in explanation.decision_summary

    @pytest.mark.asyncio
    async def test_explanation_has_evidence(self, engine: ExplanationEngine) -> None:
        agent_id = uuid4()
        result = await engine.explain(
            recommendation=_base_recommendation(),
            reasoning_chain=_base_chain(),
            agent_outputs={
                agent_id: {
                    "confidence": 0.85,
                    "evidence": [
                        {"type": "sensor_data", "source": "crowd_counter", "description": "live count"},
                        {"type": "historical", "source": "incident_db", "description": "past surge"},
                    ],
                    "agent_name": "Crowd Agent",
                },
            },
            confidence_report=_base_confidence(),
            safety_report=_base_safety(),
            user_role=UserRole.ADMIN,
            context={},
        )
        assert isinstance(result, Success)
        explanation = result.value
        assert len(explanation.evidence) >= 1

    @pytest.mark.asyncio
    async def test_explanation_has_agents_involved(self, engine: ExplanationEngine) -> None:
        agent_id = uuid4()
        result = await engine.explain(
            recommendation=_base_recommendation(),
            reasoning_chain=_base_chain(),
            agent_outputs={agent_id: {"confidence": 0.85, "evidence": [], "agent_name": "Crowd Agent"}},
            confidence_report=_base_confidence(),
            safety_report=_base_safety(),
            user_role=UserRole.COORDINATOR,
            context={},
        )
        assert isinstance(result, Success)
        explanation = result.value
        assert len(explanation.agents_involved) >= 1

    @pytest.mark.asyncio
    async def test_explanation_tradeoffs_low_confidence(self, engine: ExplanationEngine) -> None:
        agent_id = uuid4()
        low_conf = ConfidenceReport(
            overall=0.45,
            per_agent={},
            evidence_quality=0.3,
            data_freshness=0.4,
        )
        low_conf_rec = {
            "recommendation": "Proceed with caution",
            "confidence": 0.45,
            "agents_used": [{"agent_id": str(uuid4()), "agent_name": "Crowd Agent"}],
        }
        result = await engine.explain(
            recommendation=low_conf_rec,
            reasoning_chain=_base_chain(),
            agent_outputs={agent_id: {"confidence": 0.45, "evidence": [], "agent_name": "Crowd Agent"}},
            confidence_report=low_conf,
            safety_report=_base_safety(),
            user_role=UserRole.COORDINATOR,
            context={},
        )
        assert isinstance(result, Success)
        explanation = result.value
        tradeoff_text = " ".join(explanation.tradeoffs).lower()
        assert "confidence" in tradeoff_text or "moderate" in tradeoff_text

    @pytest.mark.asyncio
    async def test_explanation_limitations_degraded(self, engine: ExplanationEngine) -> None:
        agent_id = uuid4()
        result = await engine.explain(
            recommendation=_base_recommendation(),
            reasoning_chain=_base_chain(),
            agent_outputs={
                agent_id: {
                    "confidence": 0.85,
                    "evidence": [],
                    "agent_name": "Crowd Agent",
                    "_degradation": {"degraded_output": True},
                },
            },
            confidence_report=_base_confidence(),
            safety_report=_base_safety(),
            user_role=UserRole.COORDINATOR,
            context={},
        )
        assert isinstance(result, Success)
        explanation = result.value
        assert len(explanation.limitations) >= 1

    @pytest.mark.asyncio
    async def test_coordinator_moderate_depth(self, engine: ExplanationEngine) -> None:
        agent_id = uuid4()
        result = await engine.explain(
            recommendation=_base_recommendation(),
            reasoning_chain=_base_chain(),
            agent_outputs={agent_id: {"confidence": 0.85, "evidence": [], "agent_name": "Crowd Agent"}},
            confidence_report=_base_confidence(),
            safety_report=_base_safety(),
            user_role=UserRole.COORDINATOR,
            context={},
        )
        assert isinstance(result, Success)
        explanation = result.value
        assert explanation.depth_level == "moderate"
        assert "Based on" in explanation.decision_summary
