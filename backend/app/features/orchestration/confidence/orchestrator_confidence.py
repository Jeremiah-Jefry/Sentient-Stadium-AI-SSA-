from __future__ import annotations

import logging
import statistics
import time
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.features.orchestration.reasoning.reasoning_engine import ReasoningChain
from app.features.orchestration.safety.safety_engine import SafetyReport
from app.shared.result import Result

logging = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ConfidenceReport:
    overall: float
    per_agent: dict[str, float]
    agent_agreement: float
    reasoning_quality: float
    evidence_strength: float
    data_freshness: float
    safety_score: float
    knowledge_quality: float
    limiting_factors: list[str]
    alternatives_count: int


class OrchestratorConfidence:

    def __init__(self) -> None:
        self._weights = {
            "per_agent": 0.25,
            "agreement": 0.15,
            "reasoning": 0.20,
            "evidence": 0.15,
            "safety": 0.15,
            "knowledge": 0.10,
        }

    async def compute(
        self,
        step_results: dict[UUID, Result[dict]],
        agent_outputs: dict[UUID, dict[str, Any]],
        reasoning_chain: ReasoningChain,
        safety_report: SafetyReport,
    ) -> ConfidenceReport:
        start = time.monotonic()

        per_agent = self._compute_per_agent_confidence(agent_outputs)
        agreement = self._compute_agent_agreement(agent_outputs)
        reasoning = self._compute_reasoning_quality(reasoning_chain)
        evidence = self._compute_evidence_strength(agent_outputs)
        freshness = self._compute_data_freshness(agent_outputs)
        safety = self._compute_safety_score(safety_report)
        knowledge = self._compute_knowledge_quality(agent_outputs)

        overall = self._compute_overall(
            per_agent=per_agent,
            agreement=agreement,
            reasoning=reasoning,
            evidence=evidence,
            safety=safety,
            knowledge=knowledge,
        )

        limiting_factors = self._identify_limiting_factors({
            "per_agent": per_agent,
            "agreement": agreement,
            "reasoning": reasoning,
            "evidence": evidence,
            "freshness": freshness,
            "safety": safety,
            "knowledge": knowledge,
        })

        alternatives_count = self._count_alternatives(reasoning_chain)

        elapsed = (time.monotonic() - start) * 1000
        logging.info(
            "Confidence computed in %.1fms: overall=%.3f, agreement=%.3f, reasoning=%.3f",
            elapsed, overall, agreement, reasoning,
        )

        return ConfidenceReport(
            overall=round(overall, 4),
            per_agent={str(k): round(v, 4) for k, v in per_agent.items()},
            agent_agreement=round(agreement, 4),
            reasoning_quality=round(reasoning, 4),
            evidence_strength=round(evidence, 4),
            data_freshness=round(freshness, 4),
            safety_score=round(safety, 4),
            knowledge_quality=round(knowledge, 4),
            limiting_factors=limiting_factors,
            alternatives_count=alternatives_count,
        )

    def _compute_per_agent_confidence(
        self,
        agent_outputs: dict[UUID, dict[str, Any]],
    ) -> dict[UUID, float]:
        per_agent: dict[UUID, float] = {}

        for agent_id, output in agent_outputs.items():
            confidence = output.get("confidence", 0.5)
            if not isinstance(confidence, (int, float)):
                confidence = 0.5
            per_agent[agent_id] = max(0.0, min(1.0, float(confidence)))

        return per_agent

    def _compute_agent_agreement(self, outputs: dict[UUID, dict[str, Any]]) -> float:
        if len(outputs) < 2:
            return 1.0

        intents: list[str] = []
        for output in outputs.values():
            intent = output.get("intent", output.get("classification", ""))
            if intent:
                intents.append(str(intent))

        if not intents:
            return 0.5

        from collections import Counter
        counts = Counter(intents)
        most_common_count = counts.most_common(1)[0][1]

        return most_common_count / len(intents)

    def _compute_reasoning_quality(self, chain: ReasoningChain) -> float:
        if not chain.stages:
            return 0.0

        expected_stages = 8
        completed = len(chain.stages)
        completeness = completed / expected_stages

        stage_confidences = [s.confidence for s in chain.stages]
        if not stage_confidences:
            return completeness * 0.5

        avg_confidence = statistics.mean(stage_confidences)
        confidence_stdev = (
            statistics.stdev(stage_confidences)
            if len(stage_confidences) > 1 else 0.0
        )
        consistency_penalty = confidence_stdev * 0.3

        quality = (
            (completeness * 0.5) + (avg_confidence * 0.4)
            - consistency_penalty
            + (0.1 if chain.summary else 0.0)
        )

        return max(0.0, min(1.0, quality))

    def _compute_evidence_strength(self, outputs: dict[UUID, dict[str, Any]]) -> float:
        if not outputs:
            return 0.0

        total_evidence = 0
        high_quality_evidence = 0

        for output in outputs.values():
            evidence_list = output.get("evidence", output.get("data_sources", []))
            if isinstance(evidence_list, list):
                total_evidence += len(evidence_list)
                for item in evidence_list:
                    if isinstance(item, dict):
                        quality = item.get("quality", item.get("relevance_score", 0.5))
                        if isinstance(quality, (int, float)) and quality > 0.7:
                            high_quality_evidence += 1

        if total_evidence == 0:
            return 0.2

        quantity_score = min(total_evidence / 10, 1.0) * 0.4
        quality_score = (
            (high_quality_evidence / total_evidence) * 0.6
            if total_evidence > 0 else 0.0
        )

        return quantity_score + quality_score

    def _compute_data_freshness(self, outputs: dict[UUID, dict[str, Any]]) -> float:
        if not outputs:
            return 0.5

        now = time.time()
        freshness_scores: list[float] = []

        for output in outputs.values():
            timestamp = output.get("timestamp", output.get("generated_at"))
            if timestamp is None:
                freshness_scores.append(0.5)
                continue

            if isinstance(timestamp, (int, float)):
                age_seconds = now - float(timestamp)
            else:
                freshness_scores.append(0.5)
                continue

            if age_seconds < 60:
                freshness_scores.append(1.0)
            elif age_seconds < 300:
                freshness_scores.append(0.8)
            elif age_seconds < 900:
                freshness_scores.append(0.6)
            elif age_seconds < 3600:
                freshness_scores.append(0.4)
            else:
                freshness_scores.append(0.2)

        return statistics.mean(freshness_scores) if freshness_scores else 0.5

    def _compute_safety_score(self, report: SafetyReport) -> float:
        if report.is_safe:
            base_score = 1.0
        elif report.safety_level.value == "warning":
            base_score = 0.7
        elif report.safety_level.value == "dangerous":
            base_score = 0.3
        else:
            base_score = 0.0

        risk_penalty = report.overall_risk_score * 0.3
        violation_penalty = len(report.violations) * 0.05

        score = base_score - risk_penalty - violation_penalty
        return max(0.0, min(1.0, score))

    def _compute_knowledge_quality(self, outputs: dict[UUID, dict[str, Any]]) -> float:
        if not outputs:
            return 0.3

        knowledge_scores: list[float] = []

        for output in outputs.values():
            sources = output.get("knowledge_sources", output.get("sources", []))
            if not isinstance(sources, list) or not sources:
                knowledge_scores.append(0.3)
                continue

            authoritative_count = 0
            for source in sources:
                if isinstance(source, dict):
                    category = source.get("category", "")
                    if category in ("safety_sop", "emergency_procedure", "venue_rule"):
                        authoritative_count += 1

            if authoritative_count > 0:
                knowledge_scores.append(0.9)
            elif sources:
                knowledge_scores.append(0.6)
            else:
                knowledge_scores.append(0.3)

        return statistics.mean(knowledge_scores) if knowledge_scores else 0.3

    def _compute_overall(
        self,
        per_agent: dict[UUID, float],
        agreement: float,
        reasoning: float,
        evidence: float,
        safety: float,
        knowledge: float,
    ) -> float:
        avg_agent = statistics.mean(per_agent.values()) if per_agent else 0.5

        weighted = (
            avg_agent * self._weights["per_agent"]
            + agreement * self._weights["agreement"]
            + reasoning * self._weights["reasoning"]
            + evidence * self._weights["evidence"]
            + safety * self._weights["safety"]
            + knowledge * self._weights["knowledge"]
        )

        return max(0.0, min(1.0, weighted))

    @staticmethod
    def _identify_limiting_factors(scores: dict[str, float]) -> list[str]:
        factors: list[str] = []

        thresholds: dict[str, tuple[float, str]] = {
            "per_agent": (0.5, "Agent confidence below threshold"),
            "agreement": (0.5, "Agents disagree on response"),
            "reasoning": (0.4, "Reasoning chain incomplete or low quality"),
            "evidence": (0.3, "Insufficient or weak evidence"),
            "freshness": (0.4, "Data is stale or outdated"),
            "safety": (0.6, "Safety concerns detected"),
            "knowledge": (0.4, "Limited authoritative knowledge used"),
        }

        for key, (threshold, message) in thresholds.items():
            value = scores.get(key, 0.0)
            if value < threshold:
                factors.append(f"{message} ({key}={value:.2f})")

        return factors

    @staticmethod
    def _count_alternatives(chain: ReasoningChain) -> int:
        alternatives = 0
        for stage in chain.stages:
            if stage.stage.value == "plan":
                strategies = stage.output.get("strategies", [])
                alternatives = max(0, len(strategies) - 1)
                break
        return alternatives
