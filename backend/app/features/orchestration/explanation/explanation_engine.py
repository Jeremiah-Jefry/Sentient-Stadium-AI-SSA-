from __future__ import annotations

import logging
from uuid import UUID

from app.features.orchestration.explanation.types import (
    ConfidenceReport,
    Explanation,
    ReasoningChain,
    SafetyReport,
)
from app.features.orchestration.models.enums import UserRole
from app.shared.result import Failure, Result, Success

logging = logging.getLogger(__name__)

_DEPTH_BY_ROLE: dict[UserRole, str] = {
    UserRole.VOLUNTEER: "simple",
    UserRole.COORDINATOR: "moderate",
    UserRole.ADMIN: "detailed",
    UserRole.EMERGENCY_LEAD: "detailed",
    UserRole.SYSTEM: "detailed",
}

_MAX_DEPTH: dict[UserRole, int] = {
    UserRole.VOLUNTEER: 2,
    UserRole.COORDINATOR: 5,
    UserRole.ADMIN: 10,
    UserRole.EMERGENCY_LEAD: 10,
    UserRole.SYSTEM: 10,
}


class ExplanationEngine:
    def __init__(self) -> None:
        pass

    async def explain(
        self,
        recommendation: dict,
        reasoning_chain: ReasoningChain,
        agent_outputs: dict[UUID, dict],
        confidence_report: ConfidenceReport,
        safety_report: SafetyReport,
        user_role: UserRole,
        context: dict,
    ) -> Result[Explanation]:
        try:
            depth_level = _DEPTH_BY_ROLE.get(user_role, "moderate")
            max_depth = _MAX_DEPTH.get(user_role, 5)

            decision_summary = self._adjust_depth(
                self._summarize_decision(recommendation, user_role), max_depth,
            )
            reasoning_summary = self._adjust_depth(
                self._describe_reasoning(reasoning_chain, user_role), max_depth,
            )
            expected_outcome = self._adjust_depth(
                self._describe_expected_outcome(recommendation, confidence_report), max_depth,
            )

            if user_role == UserRole.EMERGENCY_LEAD:
                decision_summary = self._prepend_safety_urgency(decision_summary, safety_report)

            limitations = self._identify_limitations(agent_outputs, confidence_report)
            if user_role == UserRole.EMERGENCY_LEAD:
                limitations = limitations + list(safety_report.warnings)

            explanation = Explanation(
                decision_summary=decision_summary,
                reasoning_summary=reasoning_summary,
                evidence=self._compile_evidence(agent_outputs),
                agents_involved=self._collect_agents(agent_outputs),
                alternatives=self._describe_alternatives(agent_outputs, recommendation),
                tradeoffs=self._describe_tradeoffs(
                    recommendation, safety_report, confidence_report,
                ),
                confidence=confidence_report.overall,
                expected_outcome=expected_outcome,
                limitations=limitations,
                role_adjusted=user_role != UserRole.ADMIN,
                depth_level=depth_level,
            )

            logging.info(
                "Explanation generated for role=%s depth=%s confidence=%.2f",
                user_role.value, depth_level, confidence_report.overall,
            )
            return Success(value=explanation)
        except Exception as exc:
            logging.error("Explanation generation failed: %s", exc)
            return Failure(
                error_code="EXPLANATION_FAILED",
                message=f"Failed to generate explanation: {exc}",
            )

    def _summarize_decision(
        self, recommendation: dict, user_role: UserRole,
    ) -> str:
        action = recommendation.get(
            "recommendation",
            recommendation.get("action", "No recommendation available"),
        )
        confidence = recommendation.get("confidence", 0.0)
        agent_count = len(recommendation.get("agents_used", []))

        if user_role == UserRole.VOLUNTEER:
            return f"Recommended action: {action}"

        base = f"Recommended action: {action}. Confidence: {confidence:.0%}."
        if user_role == UserRole.COORDINATOR:
            return f"{base} Based on {agent_count} agent input(s)."

        reasoning = recommendation.get("reasoning", {})
        strategy = (
            reasoning.get("strategy", "unknown")
            if isinstance(reasoning, dict) else "unknown"
        )
        return f"{base} Strategy: {strategy}. Agents consulted: {agent_count}."

    def _describe_reasoning(
        self, chain: ReasoningChain, user_role: UserRole,
    ) -> str:
        if user_role == UserRole.VOLUNTEER:
            return (
                "The system analyzed available information"
                " and determined the best course of action."
            )

        if user_role == UserRole.COORDINATOR:
            return (
                f"Reasoning completed {chain.stage_count} stages in {chain.duration_ms:.0f}ms. "
                f"Final assessment: {chain.final_reasoning}"
            )

        parts = [
            f"{s.get('name', '?')} (conf: {s.get('confidence', 0.0):.0%})"
            for s in chain.stages
        ]
        stages_text = " -> ".join(parts) if parts else "No stages recorded"
        return (
            f"Reasoning chain ({chain.stage_count} stages, {chain.duration_ms:.0f}ms): "
            f"{stages_text}. Final: {chain.final_reasoning}"
        )

    def _compile_evidence(self, agent_outputs: dict[UUID, dict]) -> list[dict]:
        evidence: list[dict] = []
        seen: set[str] = set()

        for _agent_id, output in agent_outputs.items():
            for item in output.get("evidence", []):
                if not isinstance(item, dict):
                    continue
                source = str(item.get("source", item.get("type", "unknown")))
                if source in seen:
                    continue
                seen.add(source)
                evidence.append({
                    "source": source,
                    "type": item.get("type", "unknown"),
                    "content": item.get("description", item.get("content", "")),
                    "weight": item.get("weight", item.get("relevance", 0.5)),
                })

        return evidence

    def _collect_agents(self, agent_outputs: dict[UUID, dict]) -> list[dict]:
        agents: list[dict] = []
        for agent_id, output in agent_outputs.items():
            meta = output.get("_step_metadata", {})
            conf = output.get("confidence", 0.0)
            rec = output.get("recommendation", output.get("result", ""))
            agents.append({
                "name": output.get("agent_name", meta.get("agent_name", str(agent_id))),
                "role": output.get("agent_role", meta.get("action", "unknown")),
                "contribution": f"Confidence: {conf:.0%}, evidence: {len(output.get('evidence', []))} items: {str(rec)[:80]}",
            })
        return agents

    def _describe_alternatives(
        self, agent_outputs: dict[UUID, dict],
        recommendation: dict,
    ) -> list[dict]:
        alternatives: list[dict] = []
        seen: set[str] = set()
        primary = str(recommendation.get("recommendation", ""))

        for _agent_id, output in agent_outputs.items():
            for candidate in output.get("alternatives", output.get("recommendations", [])):
                candidate_str = str(candidate)
                if candidate_str == primary or candidate_str in seen:
                    continue
                seen.add(candidate_str)
                if isinstance(candidate, dict):
                    alternatives.append({
                        "description": candidate_str,
                        "why_rejected": (
                            candidate.get(
                                "why_rejected",
                                "Lower priority than primary"
                                " recommendation",
                            )
                        ),
                        "risk": candidate.get("risk", "unknown"),
                    })
                else:
                    alternatives.append({
                        "description": candidate_str,
                        "why_rejected": "Lower priority than primary recommendation",
                        "risk": "unknown",
                    })

        return alternatives

    def _describe_tradeoffs(
        self, recommendation: dict,
        safety_report: SafetyReport,
        confidence_report: ConfidenceReport,
    ) -> list[str]:
        tradeoffs: list[str] = []
        confidence = recommendation.get("confidence", confidence_report.overall)

        if confidence < 0.7:
            tradeoffs.append(
                f"Confidence is moderate ({confidence:.0%})."
                " Action may need verification.",
            )
        if confidence_report.data_freshness < 0.5:
            tradeoffs.append(
                "Some input data may be stale."
                " Real-time accuracy could be reduced.",
            )
        if confidence_report.evidence_quality < 0.5:
            tradeoffs.append(
                "Evidence quality is limited."
                " Recommendation relies on fewer"
                " data sources than ideal.",
            )
        if safety_report.violations:
            tradeoffs.append(
                f"Safety check flagged"
                f" {len(safety_report.violations)} violation(s)."
                " Additional precautions may be required.",
            )
        if safety_report.requires_human_review:
            tradeoffs.append(
                "Decision requires human review before"
                " execution due to safety constraints.",
            )
        if len(recommendation.get("agents_used", [])) <= 1:
            tradeoffs.append(
                "Only one agent contributed."
                " Cross-validation from additional"
                " agents is unavailable.",
            )
        if not tradeoffs:
            tradeoffs.append("No significant tradeoffs identified.")

        return tradeoffs

    def _identify_limitations(
        self, agent_outputs: dict[UUID, dict],
        confidence_report: ConfidenceReport,
    ) -> list[str]:
        limitations: list[str] = []
        degraded = [
            aid for aid, out in agent_outputs.items()
            if out.get("_degradation", {}).get("degraded_output", False)
        ]
        if degraded:
            limitations.append(
                f"{len(degraded)} agent(s) produced degraded"
                " output. Results may be incomplete.",
            )
        if confidence_report.overall < 0.5:
            limitations.append(
                "Overall confidence is low."
                " Results should be treated with caution.",
            )
        if confidence_report.data_freshness < 0.3:
            limitations.append(
                "Data freshness is poor."
                " Information may not reflect"
                " current conditions.",
            )
        return limitations

    def _describe_expected_outcome(
        self, recommendation: dict,
        confidence_report: ConfidenceReport,
    ) -> str:
        action = recommendation.get("recommendation", recommendation.get("action", ""))
        conf = confidence_report.overall
        qualifier = (
            "High confidence" if conf >= 0.8
            else "Moderate confidence" if conf >= 0.5
            else "Low confidence"
        )
        return f"{qualifier} ({conf:.0%}): {action}"

    def _prepend_safety_urgency(self, text: str, safety_report: SafetyReport) -> str:
        level = safety_report.safety_level
        if level in ("critical", "dangerous"):
            return f"[SAFETY ALERT - {level.upper()}] {text}"
        if level == "warning":
            return f"[CAUTION] {text}"
        return text

    def _adjust_depth(self, text: str, max_depth: int) -> str:
        sentences = text.split(". ")
        if len(sentences) > max_depth:
            return ". ".join(sentences[:max_depth]) + "."
        return text
