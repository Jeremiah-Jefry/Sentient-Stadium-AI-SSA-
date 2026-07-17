"""SQLAlchemy ORM models for the orchestration engine."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class ExecutionHistory(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Immutable log of every orchestrated request lifecycle."""

    __tablename__ = "orch_execution_history"

    request_id: Mapped[uuid.UUID] = mapped_column(index=True, nullable=False)
    execution_plan_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(30), index=True, nullable=False)
    strategy: Mapped[str | None] = mapped_column(String(30), nullable=True)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    reasoning: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    evidence: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    agents_used: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    alternatives: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    explanation: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    total_duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    steps_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    steps_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    metadata_: Mapped[dict | None] = mapped_column(JSONB, name="metadata", nullable=True)


class ExecutionPlan(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Execution plan containing ordered steps and dependencies."""

    __tablename__ = "orch_execution_plans"

    request_id: Mapped[uuid.UUID] = mapped_column(index=True, nullable=False)
    strategy: Mapped[str | None] = mapped_column(String(30), nullable=True)
    steps: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    dependencies: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    timeout_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    fallback_plan_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(30), index=True, nullable=False)


class ExecutionStepRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Individual step execution record within an orchestration."""

    __tablename__ = "orch_execution_steps"

    execution_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orch_execution_history.id"), index=True, nullable=False,
    )
    plan_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("orch_execution_plans.id"), nullable=True,
    )
    agent_id: Mapped[uuid.UUID | None] = mapped_column(index=True, nullable=True)
    action: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(30), index=True, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    input_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    output_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class DecisionLedger(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Audit ledger for all autonomous decisions made during orchestration."""

    __tablename__ = "orch_decision_ledger"

    execution_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orch_execution_history.id"), index=True, nullable=False,
    )
    request_id: Mapped[uuid.UUID] = mapped_column(index=True, nullable=False)
    decision: Mapped[str | None] = mapped_column(Text, nullable=True)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    agents_involved: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    evidence: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    alternatives: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    safety_level: Mapped[str | None] = mapped_column(String(30), nullable=True)


class AgentHealthRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Real-time health telemetry for each AI agent."""

    __tablename__ = "orch_agent_health"

    agent_id: Mapped[uuid.UUID] = mapped_column(index=True, nullable=False)
    agent_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(30), index=True, nullable=False)
    health_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_load: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_invocations: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    avg_latency_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    last_heartbeat: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    error_details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class ToolCallRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Record of every external tool invocation during orchestration."""

    __tablename__ = "orch_tool_calls"

    execution_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orch_execution_history.id"), index=True, nullable=False,
    )
    tool_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    tool_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    parameters: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    cache_hit: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class OrchestrationAuditLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """System-wide audit trail for orchestration events."""

    __tablename__ = "orch_audit_logs"

    execution_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orch_execution_history.id"), index=True, nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    risk_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
