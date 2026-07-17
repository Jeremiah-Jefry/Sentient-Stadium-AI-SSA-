from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from app.features.orchestration.models.enums import ReasoningStage


@dataclass(frozen=True, slots=True)
class ReasoningStageResult:
    stage: ReasoningStage
    output: dict[str, Any]
    confidence: float
    duration_ms: float
    evidence: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ReasoningChain:
    chain_id: UUID
    request_id: UUID
    stages: list[ReasoningStageResult] = field(default_factory=list)
    overall_confidence: float = 0.0
    total_duration_ms: float = 0.0
    conclusion: dict[str, Any] = field(default_factory=dict)
    summary: str = ""
