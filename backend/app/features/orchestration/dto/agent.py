"""Pydantic models for agent metadata."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.features.orchestration.models.enums import AgentStatus


class AgentCapability(BaseModel):
    """Describes a single capability an agent can perform."""

    model_config = ConfigDict(frozen=True, validate_default=True)

    name: str
    description: str
    input_schema: dict = Field(default_factory=dict)
    output_schema: dict = Field(default_factory=dict)


class AgentMetadata(BaseModel):
    """Static metadata describing a registered agent."""

    model_config = ConfigDict(frozen=True, validate_default=True)

    agent_id: UUID
    name: str
    description: str
    capabilities: list[AgentCapability] = Field(default_factory=list)
    supported_actions: list[str] = Field(default_factory=list)
    dependencies: list[UUID] = Field(default_factory=list)
    cost_per_invocation: float = Field(ge=0)
    avg_latency_ms: float = Field(ge=0)
    priority: int = Field(ge=1, le=10)
    version: str
    permissions: list[str] = Field(default_factory=list)
    supported_tools: list[UUID] = Field(default_factory=list)
    max_concurrent: int = Field(default=10, ge=1)


class RegisteredAgent(BaseModel):
    """Runtime representation of a registered agent with live state."""

    model_config = ConfigDict(frozen=True, validate_default=True)

    metadata: AgentMetadata
    status: AgentStatus
    current_load: int = Field(default=0, ge=0)
    health_score: float = Field(default=1.0, ge=0.0, le=1.0)
    last_heartbeat: datetime | None = None
    total_invocations: int = Field(default=0, ge=0)
    error_rate: float = Field(default=0.0, ge=0.0, le=1.0)
