from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from app.features.orchestration.collaboration.conflict_resolver import ConflictResolver
from app.features.orchestration.dto.agent import RegisteredAgent
from app.features.orchestration.dto.execution import ExecutionPlan
from app.shared.result import Failure, Result, Success

logging = logging.getLogger(__name__)


class ResultAggregator:
    def __init__(self) -> None:
        self._conflict_resolver = ConflictResolver()

    async def aggregate(
        self,
        step_results: dict[UUID, Result[dict]],
        plan: ExecutionPlan,
        agents: dict[UUID, RegisteredAgent],
    ) -> Result[dict]:
        successful_outputs: dict[UUID, dict] = {}
        failed_steps: list[UUID] = []

        for step_id, result in step_results.items():
            if isinstance(result, Success):
                output = result.value
                if not output.get("_degradation", {}).get("degraded_output", False):
                    successful_outputs[step_id] = output
            else:
                failed_steps.append(step_id)

        if not successful_outputs:
            return Failure(
                error_code="NO_SUCCESSFUL_OUTPUTS",
                message="All agent steps failed or produced degraded output",
                details={"failed_steps": [str(s) for s in failed_steps]},
            )

        merged = self._merge_complementary(successful_outputs)

        if len(successful_outputs) > 1:
            conflict_result = await self._conflict_resolver.resolve(
                successful_outputs, list(agents.values()),
            )
            if isinstance(conflict_result, Success):
                merged.update(conflict_result.value)

        agent_confidences: dict[UUID, float] = {}
        agent_weights: dict[UUID, float] = {}
        for step_id, output in successful_outputs.items():
            step = next((s for s in plan.steps if s.step_id == step_id), None)
            if step and step.agent_id in agents:
                agent = agents[step.agent_id]
                conf = output.get("confidence", 0.5)
                agent_confidences[step.agent_id] = conf
                agent_weights[step.agent_id] = float(agent.metadata.priority) / 10.0

        overall_confidence = self._compute_overall_confidence(agent_confidences, agent_weights)
        evidence = self._compile_evidence(successful_outputs)
        alternatives = self._build_alternatives(successful_outputs)

        recommendation = merged.get("recommendation", "")
        if not recommendation:
            recs = merged.get("recommendations", [])
            if isinstance(recs, list) and recs:
                recommendation = recs[0]

        unified_result = {
            "recommendation": str(recommendation),
            "confidence": overall_confidence,
            "reasoning": merged.get("reasoning", {}),
            "evidence": evidence,
            "alternatives": alternatives,
            "agents_used": [
                {
                    "agent_id": str(agent_id),
                    "agent_name": (
                        agents[agent_id].metadata.name
                        if agent_id in agents else "unknown"
                    ),
                    "confidence": agent_confidences.get(agent_id, 0.0),
                }
                for agent_id in successful_outputs
            ],
            "step_outputs": {str(k): v for k, v in successful_outputs.items()},
            "failed_steps": [str(s) for s in failed_steps],
            "aggregation_metadata": {
                "total_steps": len(step_results),
                "successful_steps": len(successful_outputs),
                "failed_steps": len(failed_steps),
                "conflicts_resolved": len(successful_outputs) > 1,
            },
        }

        return Success(value=unified_result)

    def _merge_complementary(self, outputs: dict[UUID, dict]) -> dict:
        merged: dict[str, Any] = {}
        key_owners: dict[str, UUID] = {}

        for step_id, output in outputs.items():
            for key, value in output.items():
                if key.startswith("_"):
                    continue
                if key not in merged:
                    merged[key] = value
                    key_owners[key] = step_id
                elif key == "evidence" and isinstance(value, list):
                    existing = merged.get(key, [])
                    if isinstance(existing, list):
                        merged[key] = existing + value
                elif key == "confidence":
                    existing_conf = merged.get(key, 0.0)
                    merged[key] = max(existing_conf, float(value))
                elif key == "recommendations" and isinstance(value, list):
                    existing_recs = merged.get(key, [])
                    if isinstance(existing_recs, list):
                        seen = {str(r) for r in existing_recs}
                        for rec in value:
                            if str(rec) not in seen:
                                existing_recs.append(rec)
                                seen.add(str(rec))
                        merged[key] = existing_recs

        return merged

    def _compute_overall_confidence(
        self,
        agent_confidences: dict[UUID, float],
        agent_weights: dict[UUID, float],
    ) -> float:
        if not agent_confidences:
            return 0.0

        total_weight = 0.0
        weighted_sum = 0.0
        for agent_id, conf in agent_confidences.items():
            weight = agent_weights.get(agent_id, 0.5)
            weighted_sum += conf * weight
            total_weight += weight

        if total_weight == 0:
            return 0.0

        return round(weighted_sum / total_weight, 4)

    def _compile_evidence(self, outputs: dict[UUID, dict]) -> list[dict]:
        all_evidence: list[dict] = []
        seen_sources: set[str] = set()

        for output in outputs.values():
            evidence_list = output.get("evidence", [])
            if not isinstance(evidence_list, list):
                continue
            for item in evidence_list:
                if not isinstance(item, dict):
                    continue
                source_key = (
                    f"{item.get('type', '')}:"
                    f"{item.get('description', item.get('source', ''))}"
                )
                if source_key not in seen_sources:
                    seen_sources.add(source_key)
                    all_evidence.append(item)

        return all_evidence

    def _build_alternatives(self, outputs: dict[UUID, dict]) -> list[dict]:
        alternatives: list[dict] = []
        seen: set[str] = set()

        for output in outputs.values():
            route_options = output.get("route_options", [])
            if isinstance(route_options, list):
                for option in route_options:
                    if isinstance(option, dict):
                        option_id = str(option.get("route_id", option.get("name", "")))
                        if option_id not in seen:
                            seen.add(option_id)
                            alternatives.append({
                                "type": "route_option",
                                "data": option,
                            })

            recs = output.get("recommendations", [])
            if isinstance(recs, list):
                for rec in recs:
                    rec_str = str(rec)
                    if rec_str not in seen:
                        seen.add(rec_str)
                        alternatives.append({
                            "type": "recommendation",
                            "data": rec,
                        })

        return alternatives
