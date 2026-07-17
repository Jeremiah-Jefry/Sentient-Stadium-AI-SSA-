"""Tests for OrchestratorConfidence — weighted confidence computation, per-agent scoring, and limiting factors."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.features.orchestration.confidence.orchestrator_confidence import OrchestratorConfidence
from app.features.orchestration.models.enums import ReasoningStage, SafetyLevel
from app.features.orchestration.reasoning.reasoning_types import (
    ReasoningChain,
    ReasoningStageResult,
)
from app.features.orchestration.safety.safety_types import SafetyReport


def _make_safety_report(
    is_safe: bool = True,
    safety_level: SafetyLevel = SafetyLevel.SAFE,
    violations: list | None = None,
    risk_score: float = 0.0,
) -> SafetyReport:
    return SafetyReport(
        safety_level=safety_level,
        is_safe=is_safe,
        violations=violations or [],
        warnings=[],
        checked_at=datetime.now(UTC),
        overall_risk_score=risk_score,
    )


def _make_reasoning_chain(
    stages: list[ReasoningStageResult] | None = None,
    summary: str = "Test reasoning chain",
) -> ReasoningChain:
    if stages is None:
        stages = [
            ReasoningStageResult(stage=ReasoningStage.OBSERVE, output={}, confidence=0.8, duration_ms=10.0),
            ReasoningStageResult(stage=ReasoningStage.THINK, output={}, confidence=0.75, duration_ms=15.0),
            ReasoningStageResult(stage=ReasoningStage.PLAN, output={"strategies": [{"name": "s1"}, {"name": "s2"}], "primary_strategy": {"name": "s1"}}, confidence=0.82, duration_ms=20.0),
            ReasoningStageResult(stage=ReasoningStage.EXECUTE, output={}, confidence=0.82, duration_ms=5.0),
            ReasoningStageResult(stage=ReasoningStage.CRITIQUE, output={}, confidence=0.78, duration_ms=8.0),
            ReasoningStageResult(stage=ReasoningStage.IMPROVE, output={}, confidence=0.80, duration_ms=6.0),
            ReasoningStageResult(stage=ReasoningStage.VALIDATE, output={}, confidence=0.85, duration_ms=4.0),
            ReasoningStageResult(stage=ReasoningStage.EXPLAIN, output={}, confidence=0.81, duration_ms=3.0),
        ]
    return ReasoningChain(
        chain_id=uuid4(),
        request_id=uuid4(),
        stages=stages,
        overall_confidence=sum(s.confidence for s in stages) / len(stages) if stages else 0.0,
        total_duration_ms=sum(s.duration_ms for s in stages),
        summary=summary,
    )


@pytest.fixture
def confidence_engine() -> OrchestratorConfidence:
    return OrchestratorConfidence()


class TestOrchestratorConfidence:

    def test_per_agent_confidence_computation(self, confidence_engine: OrchestratorConfidence) -> None:
        agent_a = uuid4()
        agent_b = uuid4()
        agent_outputs = {
            agent_a: {"confidence": 0.9, "evidence": []},
            agent_b: {"confidence": 0.6, "evidence": []},
        }
        per_agent = confidence_engine._compute_per_agent_confidence(agent_outputs)
        assert per_agent[agent_a] == 0.9
        assert per_agent[agent_b] == 0.6

    def test_per_agent_clamps_values(self, confidence_engine: OrchestratorConfidence) -> None:
        agent_id = uuid4()
        per_agent = confidence_engine._compute_per_agent_confidence({agent_id: {"confidence": 1.5}})
        assert per_agent[agent_id] == 1.0
        per_agent = confidence_engine._compute_per_agent_confidence({agent_id: {"confidence": -0.5}})
        assert per_agent[agent_id] == 0.0

    def test_per_agent_missing_confidence(self, confidence_engine: OrchestratorConfidence) -> None:
        agent_id = uuid4()
        per_agent = confidence_engine._compute_per_agent_confidence({agent_id: {}})
        assert per_agent[agent_id] == 0.5

    def test_agent_agreement_single_agent(self, confidence_engine: OrchestratorConfidence) -> None:
        agent_id = uuid4()
        agreement = confidence_engine._compute_agent_agreement({agent_id: {"intent": "navigation"}})
        assert agreement == 1.0

    def test_agent_agreement_unanimous(self, confidence_engine: OrchestratorConfidence) -> None:
        outputs = {
            uuid4(): {"intent": "crowd_management"},
            uuid4(): {"intent": "crowd_management"},
            uuid4(): {"intent": "crowd_management"},
        }
        agreement = confidence_engine._compute_agent_agreement(outputs)
        assert agreement == 1.0

    def test_agent_agreement_split(self, confidence_engine: OrchestratorConfidence) -> None:
        outputs = {
            uuid4(): {"intent": "crowd_management"},
            uuid4(): {"intent": "navigation"},
            uuid4(): {"intent": "crowd_management"},
        }
        agreement = confidence_engine._compute_agent_agreement(outputs)
        assert 0.5 < agreement < 1.0

    def test_agent_agreement_no_intents(self, confidence_engine: OrchestratorConfidence) -> None:
        outputs = {
            uuid4(): {"confidence": 0.8},
            uuid4(): {"confidence": 0.7},
        }
        agreement = confidence_engine._compute_agent_agreement(outputs)
        assert agreement == 0.5

    def test_reasoning_quality(self, confidence_engine: OrchestratorConfidence) -> None:
        chain = _make_reasoning_chain()
        quality = confidence_engine._compute_reasoning_quality(chain)
        assert 0.0 <= quality <= 1.0
        assert quality > 0.3

    def test_reasoning_quality_empty(self, confidence_engine: OrchestratorConfidence) -> None:
        chain = _make_reasoning_chain(stages=[])
        quality = confidence_engine._compute_reasoning_quality(chain)
        assert quality == 0.0

    def test_evidence_strength(self, confidence_engine: OrchestratorConfidence) -> None:
        outputs = {
            uuid4(): {
                "evidence": [
                    {"type": "sensor_data", "quality": 0.95},
                    {"type": "historical", "quality": 0.8},
                    {"type": "knowledge_base", "quality": 0.9},
                ],
            },
        }
        strength = confidence_engine._compute_evidence_strength(outputs)
        assert strength > 0.3

    def test_evidence_strength_empty(self, confidence_engine: OrchestratorConfidence) -> None:
        strength = confidence_engine._compute_evidence_strength({})
        assert strength == 0.0

    def test_safety_score_safe(self, confidence_engine: OrchestratorConfidence) -> None:
        report = _make_safety_report(is_safe=True, risk_score=0.0)
        score = confidence_engine._compute_safety_score(report)
        assert score == 1.0

    def test_safety_score_unsafe(self, confidence_engine: OrchestratorConfidence) -> None:
        safe_report = _make_safety_report(is_safe=True, risk_score=0.0)
        unsafe_report = _make_safety_report(
            is_safe=False,
            safety_level=SafetyLevel.DANGEROUS,
            violations=[{"severity": "high"}],
            risk_score=0.6,
        )
        safe_score = confidence_engine._compute_safety_score(safe_report)
        unsafe_score = confidence_engine._compute_safety_score(unsafe_report)
        assert safe_score > unsafe_score

    def test_knowledge_quality_with_sources(self, confidence_engine: OrchestratorConfidence) -> None:
        outputs = {
            uuid4(): {"sources": [{"category": "safety_sop"}, {"category": "emergency_procedure"}]},
        }
        quality = confidence_engine._compute_knowledge_quality(outputs)
        assert quality == 0.9

    def test_knowledge_quality_no_sources(self, confidence_engine: OrchestratorConfidence) -> None:
        outputs = {uuid4(): {"confidence": 0.8}}
        quality = confidence_engine._compute_knowledge_quality(outputs)
        assert quality == 0.3

    def test_overall_computation(self, confidence_engine: OrchestratorConfidence) -> None:
        overall = confidence_engine._compute_overall(
            per_agent={uuid4(): 0.9},
            agreement=0.85,
            reasoning=0.8,
            evidence=0.7,
            safety=1.0,
            knowledge=0.9,
        )
        assert 0.0 <= overall <= 1.0
        assert overall > 0.5

    def test_limiting_factors_identified(self, confidence_engine: OrchestratorConfidence) -> None:
        scores = {
            "per_agent": 0.3,
            "agreement": 0.4,
            "reasoning": 0.3,
            "evidence": 0.2,
            "freshness": 0.2,
            "safety": 0.4,
            "knowledge": 0.2,
        }
        factors = OrchestratorConfidence._identify_limiting_factors(scores)
        assert len(factors) >= 3
        factor_text = " ".join(factors).lower()
        assert "agent" in factor_text or "agreement" in factor_text

    def test_limiting_factors_none(self, confidence_engine: OrchestratorConfidence) -> None:
        scores = {
            "per_agent": 0.9,
            "agreement": 0.9,
            "reasoning": 0.9,
            "evidence": 0.9,
            "freshness": 0.9,
            "safety": 0.9,
            "knowledge": 0.9,
        }
        factors = OrchestratorConfidence._identify_limiting_factors(scores)
        assert len(factors) == 0

    def test_count_alternatives(self, confidence_engine: OrchestratorConfidence) -> None:
        chain = _make_reasoning_chain()
        count = OrchestratorConfidence._count_alternatives(chain)
        assert count == 1

    def test_count_alternatives_empty(self, confidence_engine: OrchestratorConfidence) -> None:
        chain = _make_reasoning_chain(stages=[])
        count = OrchestratorConfidence._count_alternatives(chain)
        assert count == 0

    def test_data_freshness_recent(self, confidence_engine: OrchestratorConfidence) -> None:
        import time
        now = time.time()
        outputs = {uuid4(): {"timestamp": now - 10}}
        freshness = confidence_engine._compute_data_freshness(outputs)
        assert freshness == 1.0

    def test_data_freshness_stale(self, confidence_engine: OrchestratorConfidence) -> None:
        import time
        now = time.time()
        outputs = {uuid4(): {"timestamp": now - 7200}}
        freshness = confidence_engine._compute_data_freshness(outputs)
        assert freshness < 0.5

    def test_data_freshness_no_timestamp(self, confidence_engine: OrchestratorConfidence) -> None:
        outputs = {uuid4(): {"confidence": 0.8}}
        freshness = confidence_engine._compute_data_freshness(outputs)
        assert freshness == 0.5
