from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ReasoningChain:
    stages: list[dict]
    final_reasoning: str = ""
    stage_count: int = 0
    duration_ms: float = 0.0


@dataclass(frozen=True, slots=True)
class ConfidenceReport:
    overall: float = 0.0
    per_agent: dict[str, float] = field(default_factory=dict)
    evidence_quality: float = 0.0
    data_freshness: float = 0.0
    reasoning: str = ""


@dataclass(frozen=True, slots=True)
class SafetyReport:
    safety_level: str = "safe"
    violations: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    requires_human_review: bool = False


@dataclass(frozen=True, slots=True)
class Explanation:
    decision_summary: str
    reasoning_summary: str
    evidence: list[dict]
    agents_involved: list[dict]
    alternatives: list[dict]
    tradeoffs: list[str]
    confidence: float
    expected_outcome: str
    limitations: list[str]
    role_adjusted: bool
    depth_level: str
