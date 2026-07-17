from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from app.features.orchestration.dto.agent import RegisteredAgent
from app.features.orchestration.models.enums import ConflictResolutionStrategy
from app.shared.result import Result, Success

logging = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Conflict:
    conflict_id: UUID
    field_path: str
    values: dict[UUID, Any]
    agents: list[UUID]
    severity: str


class ConflictResolver:
    def __init__(
        self,
        strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.EVIDENCE_WEIGHTED,
    ) -> None:
        self._strategy = strategy

    async def resolve(
        self,
        agent_outputs: dict[UUID, dict],
        agents: list[RegisteredAgent],
    ) -> Result[dict]:
        if len(agent_outputs) <= 1:
            if agent_outputs:
                return Success(value=next(iter(agent_outputs.values())))
            return Success(value={})

        conflicts = self._detect_conflicts(agent_outputs)

        if not conflicts:
            merged: dict[str, Any] = {}
            for output in agent_outputs.values():
                for key, value in output.items():
                    if not key.startswith("_"):
                        merged[key] = value
            return Success(value=merged)

        agents_by_id = {a.metadata.agent_id: a for a in agents}
        winning_output: dict[str, Any] = {}

        if self._strategy == ConflictResolutionStrategy.PRIORITY_BASED:
            scores = self._score_by_priority(agent_outputs, agents)
            winner_id = max(scores, key=lambda k: scores[k])
            winning_output = dict(agent_outputs[winner_id])

        elif self._strategy == ConflictResolutionStrategy.VOTING:
            winning_output = self._majority_vote(agent_outputs)

        elif self._strategy == ConflictResolutionStrategy.EVIDENCE_WEIGHTED:
            scores = self._score_by_evidence(agent_outputs)
            winner_id = max(scores, key=lambda k: scores[k])
            winning_output = dict(agent_outputs[winner_id])

        elif self._strategy == ConflictResolutionStrategy.CONFIDENCE_BASED:
            scores = self._score_by_confidence(agent_outputs)
            winner_id = max(scores, key=lambda k: scores[k])
            winning_output = dict(agent_outputs[winner_id])

        elif self._strategy == ConflictResolutionStrategy.NEWEST_WINS:
            latest_time = ""
            winner_id = next(iter(agent_outputs))
            for agent_id, output in agent_outputs.items():
                ts = output.get("_timestamp", "")
                if ts > latest_time:
                    latest_time = ts
                    winner_id = agent_id
            winning_output = dict(agent_outputs[winner_id])

        explanation = self._generate_explanation(conflicts, winning_output, self._strategy)
        winning_output["_conflict_resolution"] = {
            "strategy": self._strategy.value,
            "conflicts_detected": len(conflicts),
            "explanation": explanation,
            "participating_agents": [
                {"agent_id": str(a), "agent_name": agents_by_id[a].metadata.name}
                for a in agent_outputs.keys()
                if a in agents_by_id
            ],
        }

        return Success(value=winning_output)

    def _detect_conflicts(self, outputs: dict[UUID, dict]) -> list[Conflict]:
        conflicts: list[Conflict] = []
        all_keys: set[str] = set()

        for output in outputs.values():
            all_keys.update(k for k in output.keys() if not k.startswith("_"))

        for key in all_keys:
            values: dict[UUID, Any] = {}
            for agent_id, output in outputs.items():
                if key in output:
                    values[agent_id] = output[key]

            if len(values) <= 1:
                continue

            distinct_values = set()
            for v in values.values():
                distinct_values.add(str(v))

            if len(distinct_values) > 1:
                severity = "low"
                if key in ("recommendations", "risk_assessment", "response_plan", "decision"):
                    severity = "high"
                elif key in ("confidence", "crowd_density", "assessment"):
                    severity = "medium"

                conflicts.append(
                    Conflict(
                        conflict_id=uuid4(),
                        field_path=key,
                        values=values,
                        agents=list(values.keys()),
                        severity=severity,
                    ),
                )

        return conflicts

    def _score_by_priority(
        self,
        outputs: dict[UUID, dict],
        agents: list[RegisteredAgent],
    ) -> dict[UUID, float]:
        agent_priorities = {a.metadata.agent_id: a.metadata.priority for a in agents}
        scores: dict[UUID, float] = {}
        for agent_id in outputs:
            scores[agent_id] = float(agent_priorities.get(agent_id, 5))
        return scores

    def _score_by_evidence(self, outputs: dict[UUID, dict]) -> dict[UUID, float]:
        scores: dict[UUID, float] = {}
        for agent_id, output in outputs.items():
            evidence_list = output.get("evidence", [])
            if not isinstance(evidence_list, list):
                scores[agent_id] = 0.0
                continue

            evidence_score = 0.0
            for item in evidence_list:
                if isinstance(item, dict):
                    if item.get("type") in ("sensor_data", "real_time", "real_time_sensor"):
                        evidence_score += 1.0
                    elif item.get("type") in ("historical", "historical_memory"):
                        evidence_score += 0.7
                    elif item.get("type") in ("knowledge_base", "medical_protocol", "venue_config"):
                        evidence_score += 0.9
                    else:
                        evidence_score += 0.5

            scores[agent_id] = evidence_score / max(len(evidence_list), 1)

        return scores

    def _score_by_confidence(self, outputs: dict[UUID, dict]) -> dict[UUID, float]:
        scores: dict[UUID, float] = {}
        for agent_id, output in outputs.items():
            scores[agent_id] = float(output.get("confidence", 0.5))
        return scores

    def _majority_vote(self, outputs: dict[UUID, dict]) -> dict:
        decision_counts: Counter[str] = Counter()
        decision_to_output: dict[str, dict] = {}

        for _, output in outputs.items():
            recommendation = output.get("recommendation", "")
            if not recommendation:
                recs = output.get("recommendations", [])
                if isinstance(recs, list) and recs:
                    recommendation = str(recs[0])

            if recommendation:
                decision_counts[recommendation] += 1
                decision_to_output[recommendation] = output

        if not decision_counts:
            return dict(next(iter(outputs.values())))

        winning_decision = decision_counts.most_common(1)[0][0]
        return decision_to_output[winning_decision]

    def _generate_explanation(
        self,
        conflicts: list[Conflict],
        resolution: dict,
        strategy: ConflictResolutionStrategy,
    ) -> dict:
        high_severity = [c for c in conflicts if c.severity == "high"]
        medium_severity = [c for c in conflicts if c.severity == "medium"]

        return {
            "strategy_used": strategy.value,
            "total_conflicts": len(conflicts),
            "high_severity_conflicts": len(high_severity),
            "medium_severity_conflicts": len(medium_severity),
            "conflicting_fields": [c.field_path for c in conflicts],
            "resolution_summary": (
                f"Resolved {len(conflicts)} conflicts using {strategy.value} strategy. "
                f"Output selected based on {strategy.value.replace('_', ' ')} criteria."
            ),
            "safety_note": (
                "High-severity conflicts detected in decision fields. "
                "Human review recommended for safety-critical decisions."
                if high_severity
                else None
            ),
        }
