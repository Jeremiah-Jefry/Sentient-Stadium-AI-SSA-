"""Pydantic models for incoming orchestration requests."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.features.orchestration.models.enums import IntentType, RequestType, UserRole


class OrchestratorRequest(BaseModel):
    """Top-level request submitted to the orchestration engine."""

    model_config = ConfigDict(frozen=True, validate_default=True)

    request_id: UUID
    request_type: RequestType
    intent: IntentType | None = None
    query: str
    context: dict = Field(default_factory=dict)
    venue_id: UUID | None = None
    zone_id: UUID | None = None
    user_id: UUID | None = None
    user_role: UserRole
    priority: int = Field(default=5, ge=1, le=10)
    timeout_seconds: float = Field(default=30.0, gt=0)
    metadata: dict = Field(default_factory=dict)
    constraints: list[str] = Field(default_factory=list)


class ContextPayload(BaseModel):
    """Aggregated contextual data for a single orchestration request."""

    model_config = ConfigDict(frozen=True, validate_default=True)

    venue_id: UUID
    zone_id: UUID | None = None
    entity_ids: list[UUID] = Field(default_factory=list)
    sensor_data: dict = Field(default_factory=dict)
    crowd_data: dict = Field(default_factory=dict)
    weather_data: dict = Field(default_factory=dict)
    event_data: dict = Field(default_factory=list)
    match_phase: str | None = None
    accessibility_needs: list[str] = Field(default_factory=list)


class AgentSelectorCriteria(BaseModel):
    """Constraints used to select agents for a given execution step."""

    model_config = ConfigDict(frozen=True, validate_default=True)

    required_capabilities: list[str] = Field(default_factory=list)
    preferred_agents: list[UUID] | None = None
    excluded_agents: list[UUID] | None = None
    max_cost: float | None = None
    max_latency_ms: float | None = None


class ToolInvocationRequest(BaseModel):
    """Request to invoke a single tool within an orchestration step."""

    model_config = ConfigDict(frozen=True, validate_default=True)

    tool_id: UUID
    parameters: dict = Field(default_factory=dict)
    timeout_seconds: float = Field(default=10.0, gt=0)
