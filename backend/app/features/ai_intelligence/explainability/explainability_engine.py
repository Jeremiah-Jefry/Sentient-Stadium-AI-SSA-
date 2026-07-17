"""Explainable AI engine — structured human-readable explanations."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

MAX_FACTORS: int = 5
MAX_EVIDENCE: int = 10

# ---------------------------------------------------------------------------
# Factor description templates
# ---------------------------------------------------------------------------
_FACTOR_DESCRIPTIONS: dict[str, str] = {
    "density": "Crowd density relative to safe capacity",
    "flow": "Pedestrian flow rate vs expected throughput",
    "weather": "Weather conditions impacting safety or comfort",
    "medical": "Medical event pressure on available resources",
    "security": "Security incident volume and severity",
    "accessibility": "Blockage of routes used by disabled visitors",
    "transport": "Transport delays affecting arrival/departure surge",
    "volunteer": "Shortfall of available volunteers",
    "equipment": "Sensor and camera equipment failure rate",
    "match_context": "Match phase and score influencing crowd tension",
}

_RISK_LEVEL_DESCRIPTIONS: dict[str, str] = {
    "green": "No significant risk — normal operations",
    "yellow": "Elevated risk — monitor closely",
    "orange": "High risk — prepare countermeasures",
    "red": "Severe risk — immediate action required",
    "critical": "Critical risk — emergency protocols activate",
}


@dataclass(slots=True)
class Explanation:
    """Structured output of an XAI explanation."""

    summary: str
    reason: str
    evidence: list[dict] = field(default_factory=list)
    contributing_factors: list[dict] = field(default_factory=list)
    confidence: float = 0.0
    alternatives_considered: list[dict] = field(default_factory=list)
    tradeoffs: list[dict] = field(default_factory=list)
    expected_outcome: str = ""


class ExplainabilityEngine:
    """Generates structured explanations for AI outputs.

    Each explanation includes a one-sentence summary, a detailed reason
    citing specific factors, ranked contributing factors, cited evidence,
    and alternatives considered.
    """

    def explain_risk(
        self,
        risk_assessment: dict,
        events: list[dict],
        context: dict,
    ) -> Explanation:
        """Generate human-readable explanation for a risk assessment."""
        risk_level = risk_assessment.get("risk_level", "unknown")
        risk_score = risk_assessment.get("risk_score", 0.0)
        risk_factors = risk_assessment.get("risk_factors", {})
        contributing_ids = risk_assessment.get("contributing_events", [])

        top_factors = self._rank_top_factors(risk_factors)
        evidence = self._gather_evidence(events, contributing_ids, MAX_EVIDENCE)

        summary = (
            f"Overall risk level is {risk_level} "
            f"(score {risk_score:.0%}) "
            f"driven primarily by "
            f"{self._factor_label(top_factors[0]) if top_factors else 'multiple factors'}."
        )

        factor_details = [
            {
                "factor": f,
                "value": risk_factors.get(f, 0.0),
                "weight": _FACTOR_DESCRIPTIONS.get(f, f),
                "contribution_pct": round(
                    risk_factors.get(f, 0.0) / max(risk_score, 0.01) * 100, 1,
                ) if risk_score > 0 else 0.0,
            }
            for f in top_factors
        ]

        reason_parts = []
        for fd in factor_details[:3]:
            reason_parts.append(
                f"{fd['weight']} contributed {fd['contribution_pct']:.0f}% "
                f"with a score of {fd['value']:.2f}."
            )
        reason = " ".join(reason_parts) if reason_parts else "Risk is within normal parameters."

        return Explanation(
            summary=summary,
            reason=reason,
            evidence=evidence,
            contributing_factors=factor_details,
            confidence=risk_score,
            expected_outcome=_RISK_LEVEL_DESCRIPTIONS.get(risk_level, "Unknown"),
        )

    def explain_prediction(
        self,
        prediction: dict,
        events: list[dict],
        context: dict,
    ) -> Explanation:
        """Generate explanation for a prediction."""
        pred_type = prediction.get("prediction_type", "unknown")
        value = prediction.get("predicted_value", 0.0)
        confidence = prediction.get("confidence", 0.0)
        factors = prediction.get("contributing_factors", [])
        evidence_count = prediction.get("evidence_count", 0)

        summary = (
            f"Predicted {pred_type} with {value:.0%} likelihood "
            f"at {confidence:.0%} confidence based on {evidence_count} data points."
        )

        factor_lines = []
        for f in factors[:MAX_FACTORS]:
            name = f.get("name", f.get("rule", "unknown"))
            val = f.get("value", 0.0)
            factor_lines.append(f"{name}: {val}")

        reason = (
            f"The model predicts {pred_type} with a value of {value:.4f}. "
            f"Key factors: {'; '.join(factor_lines)}."
            if factor_lines
            else f"The model predicts {pred_type} but contributing factors are unavailable."
        )

        return Explanation(
            summary=summary,
            reason=reason,
            evidence=[{"source": "prediction_model", "evidence_count": evidence_count}],
            contributing_factors=factors[:MAX_FACTORS],
            confidence=confidence,
            expected_outcome=f"Expect {pred_type} within the prediction window.",
        )

    def explain_decision(
        self,
        decision: dict,
        alternatives: list[dict],
        context: dict,
    ) -> Explanation:
        """Generate full explanation for a selected decision."""
        intervention = decision.get("intervention_type", "unknown")
        confidence = decision.get("confidence", 0.0)
        reasoning = decision.get("reasoning", {})
        expected = decision.get("expected_outcome", {})

        summary = (
            f"Selected intervention: {intervention} "
            f"with {confidence:.0%} confidence."
        )

        alt_summaries = []
        alt_list: list[dict] = []
        for alt in alternatives[:5]:
            alt_type = alt.get("intervention_type", "unknown")
            alt_conf = alt.get("confidence", 0.0)
            alt_list.append({"type": alt_type, "confidence": alt_conf})
            alt_summaries.append(f"{alt_type} ({alt_conf:.0%})")

        rejected = [
            {"type": a["type"], "reason": "Lower confidence or higher cost"}
            for a in alt_list
            if a["type"] != intervention
        ]

        reason = (
            f"Chose {intervention} over {', '.join(alt_summaries) or 'no alternatives'} "
            f"because it scored highest on risk reduction and confidence."
        )

        tradeoffs = [
            {
                "aspect": "risk_reduction",
                "selected": expected.get("risk_reduction", 0.0),
            },
            {
                "aspect": "execution_speed",
                "selected": expected.get("speed", "moderate"),
            },
        ]

        return Explanation(
            summary=summary,
            reason=reason,
            evidence=reasoning.get("evidence", []),
            contributing_factors=reasoning.get("factors", []),
            confidence=confidence,
            alternatives_considered=alt_list,
            tradeoffs=tradeoffs,
            expected_outcome=str(expected.get("description", "Improved safety")),
        )

    def format_volunteer_briefing(self, explanation: Explanation) -> str:
        """Format an explanation into a concise volunteer-ready message."""
        lines = [explanation.summary]

        if explanation.contributing_factors:
            top = explanation.contributing_factors[0]
            if isinstance(top, dict):
                factor_name = top.get("factor") or top.get("name") or top.get("type", "")
                lines.append(f"Main factor: {factor_name}")

        if explanation.expected_outcome:
            lines.append(f"Expected: {explanation.expected_outcome}")

        lines.append(f"Confidence: {explanation.confidence:.0%}")

        return " | ".join(lines)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _rank_top_factors(self, factors: dict[str, float]) -> list[str]:
        ranked = sorted(factors.items(), key=lambda item: item[1], reverse=True)
        return [k for k, _ in ranked[:MAX_FACTORS]]

    def _gather_evidence(
        self, events: list[dict], event_ids: list[str], limit: int,
    ) -> list[dict]:
        evidence: list[dict] = []
        id_set = set(event_ids)
        for event in events:
            if len(evidence) >= limit:
                break
            eid = event.get("id", event.get("event_id", ""))
            if eid in id_set or not id_set:
                evidence.append({
                    "event_id": eid,
                    "type": event.get("type", "unknown"),
                    "description": event.get("description", ""),
                    "severity": event.get("severity", 0),
                })
        return evidence

    @staticmethod
    def _factor_label(factor_key: str) -> str:
        return _FACTOR_DESCRIPTIONS.get(factor_key, factor_key)
