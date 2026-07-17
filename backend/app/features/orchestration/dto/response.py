"""Pydantic models for orchestration outputs."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.features.orchestration.models.enums import ExecutionStatus, StreamingEventType


class OrchestratorResponse(BaseModel):
    """Final response returned by the orchestration engine."""

    model_config = ConfigDict(frozen=True, validate_default=True)

    request_id: UUID
    execution_id: UUID
    status: ExecutionStatus
    recommendation: str
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: dict = Field(default_factory=dict)
    evidence: list[dict] = Field(default_factory=list)
    agents_used: list[dict] = Field(default_factory=list)
    alternatives: list[dict] = Field(default_factory=list)
    explanation: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)
    created_at: datetime


class ExecutionStepResponse(BaseModel):
    """Response representation of a single execution step."""

    model_config = ConfigDict(frozen=True, validate_default=True)

    step_id: UUID
    agent_id: UUID
    agent_name: str
    action: str
    status: str
    dependencies: list[UUID] = Field(default_factory=list)
    timeout_seconds: float = Field(gt=0)
    is_parallel: bool = False


class ExecutionPlanResponse(BaseModel):
    """Response representation of an execution plan."""

    model_config = ConfigDict(frozen=True, validate_default=True)

    plan_id: UUID
    steps: list[ExecutionStepResponse] = Field(default_factory=list)
    strategy: str
    estimated_duration_ms: float = Field(ge=0)
    estimated_cost: float = Field(ge=0)


class AgentStatusResponse(BaseModel):
    """Current status of a registered agent."""

    model_config = ConfigDict(frozen=True, validate_default=True)

    agent_id: UUID
    name: str
    status: str
    capabilities: list[str] = Field(default_factory=list)
    current_load: int = Field(ge=0)
    health_score: float = Field(ge=0.0, le=1.0)
    last_heartbeat: datetime | None = None


class StreamingChunk(BaseModel):
    """A single event chunk emitted over the streaming channel."""

    model_config = ConfigDict(frozen=True, validate_default=True)

    event_type: StreamingEventType
    data: dict = Field(default_factory=dict)
    timestamp: datetime
    execution_id: UUID
    step_id: UUID | None = None


class ConflictResolutionResponse(BaseModel):
    """Result of a multi-agent conflict resolution process."""

    model_config = ConfigDict(frozen=True, validate_default=True)

    conflict_id: UUID
    resolution_strategy: str
    participants: list[dict] = Field(default_factory=list)
    resolution: dict = Field(default_factory=dict)
    confidence: float = Field(ge=0.0, le=1.0)


class ConfidenceReportResponse(BaseModel):
    """Detailed confidence breakdown for an orchestration decision."""

    model_config = ConfigDict(frozen=True, validate_default=True)

    overall: float = Field(ge=0.0, le=1.0)
    breakdown: dict = Field(default_factory=dict)
    per_agent: dict[UUID, float] = Field(default_factory=dict)
    evidence_quality: float = Field(ge=0.0, le=1.0)
    data_freshness: float = Field(ge=0.0, le=1.0)
    reasoning: str = ""
