"""Pydantic models for execution plans, records, and audit entries."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.features.orchestration.models.enums import (
    ExecutionStatus,
    ExecutionStrategy,
    SafetyLevel,
    StepStatus,
)


class RetryPolicy(BaseModel):
    """Retry configuration for an execution step."""

    model_config = ConfigDict(frozen=True, validate_default=True)

    max_retries: int = Field(default=3, ge=0)
    backoff_seconds: float = Field(default=1.0, ge=0)
    backoff_multiplier: float = Field(default=2.0, ge=1.0)


class ExecutionStep(BaseModel):
    """Single step within an execution plan."""

    model_config = ConfigDict(frozen=True, validate_default=True)

    step_id: UUID
    agent_id: UUID
    agent_name: str
    action: str
    parameters: dict = Field(default_factory=dict)
    timeout_seconds: float = Field(gt=0)
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    is_parallel: bool = False
    depends_on: list[UUID] = Field(default_factory=list)
    order: int = Field(ge=0)


class ExecutionPlan(BaseModel):
    """Complete execution plan with steps and dependency graph."""

    model_config = ConfigDict(frozen=True, validate_default=True)

    plan_id: UUID
    strategy: ExecutionStrategy
    steps: list[ExecutionStep] = Field(default_factory=list)
    dependencies: dict[UUID, list[UUID]] = Field(default_factory=dict)
    timeout_seconds: float = Field(gt=0)
    fallback_plan_id: UUID | None = None


class ExecutionRecord(BaseModel):
    """Persisted record of a completed or in-progress execution."""

    model_config = ConfigDict(frozen=True, validate_default=True)

    execution_id: UUID
    plan_id: UUID
    status: ExecutionStatus
    started_at: datetime
    completed_at: datetime | None = None
    duration_ms: float | None = None
    steps_completed: int = Field(ge=0)
    steps_failed: int = Field(ge=0)
    total_steps: int = Field(ge=0)


class StepRecord(BaseModel):
    """Persisted record of a single execution step outcome."""

    model_config = ConfigDict(frozen=True, validate_default=True)

    step_id: UUID
    execution_id: UUID
    agent_id: UUID
    action: str
    status: StepStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: float | None = None
    input_data: dict = Field(default_factory=dict)
    output_data: dict | None = None
    error: str | None = None
    retry_count: int = Field(default=0, ge=0)


class DecisionLedgerEntry(BaseModel):
    """Immutable ledger entry recording an orchestration decision."""

    model_config = ConfigDict(frozen=True, validate_default=True)

    decision_id: UUID
    execution_id: UUID
    request_id: UUID
    decision: str
    reasoning: str
    confidence: float = Field(ge=0.0, le=1.0)
    agents_involved: list[UUID] = Field(default_factory=list)
    evidence: list[dict] = Field(default_factory=list)
    alternatives: list[dict] = Field(default_factory=list)
    safety_level: SafetyLevel
    created_at: datetime


class AuditLogEntry(BaseModel):
    """Append-only audit log entry for compliance tracking."""

    model_config = ConfigDict(frozen=True, validate_default=True)

    log_id: UUID
    execution_id: UUID
    event_type: str
    actor_id: UUID | None = None
    details: dict = Field(default_factory=dict)
    risk_score: float = Field(default=0.0, ge=0.0, le=1.0)
    created_at: datetime
