"""Pydantic models for tool metadata."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ToolMetadata(BaseModel):
    """Static metadata describing a registered tool."""

    model_config = ConfigDict(frozen=True, validate_default=True, populate_by_name=True)

    tool_id: UUID
    name: str
    description: str
    input_schema: dict = Field(default_factory=dict, alias="schema")
    version: str
    timeout_seconds: float = Field(default=10.0, gt=0)
    cache_ttl_seconds: float = Field(default=0.0, ge=0)
    max_retries: int = Field(default=3, ge=0)
    requires_authorization: bool = True
    permissions: list[str] = Field(default_factory=list)


class ToolInvocationResult(BaseModel):
    """Result returned after a tool invocation completes."""

    model_config = ConfigDict(frozen=True, validate_default=True)

    tool_id: UUID
    success: bool
    result: dict | None = None
    error: str | None = None
    duration_ms: float = Field(ge=0)
    cache_hit: bool = False
