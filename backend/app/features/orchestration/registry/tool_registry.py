"""Dynamic tool registry — runtime registration and discovery of AI tools."""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import UUID

from app.features.orchestration.dto.tool import ToolMetadata
from app.shared.result import Failure, Result, Success

logger = logging.getLogger(__name__)


class ToolRegistry:
    """In-memory, thread-safe registry for all orchestrator-invokable tools."""

    def __init__(self) -> None:
        self._tools: dict[UUID, ToolMetadata] = {}
        self._lock = asyncio.Lock()
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        defaults = [
            _digital_twin_query_tool(),
            _routing_engine_tool(),
            _prediction_engine_tool(),
            _knowledge_search_tool(),
            _memory_search_tool(),
            _weather_service_tool(),
            _transit_service_tool(),
            _simulation_engine_tool(),
            _analytics_service_tool(),
            _incident_engine_tool(),
        ]
        for tool in defaults:
            self._tools[tool.tool_id] = tool

    async def register_tool(self, metadata: ToolMetadata) -> Result[ToolMetadata]:
        async with self._lock:
            if metadata.tool_id in self._tools:
                return Failure(
                    error_code="TOOL_ALREADY_REGISTERED",
                    message=f"Tool '{metadata.tool_id}' already exists",
                )
            self._tools[metadata.tool_id] = metadata
            logger.info("Tool registered: %s (%s)", metadata.name, metadata.tool_id)
            return Success(metadata)

    async def unregister_tool(self, tool_id: UUID) -> Result[None]:
        async with self._lock:
            if tool_id not in self._tools:
                return Failure(
                    error_code="TOOL_NOT_FOUND",
                    message=f"Tool '{tool_id}' not found",
                )
            removed = self._tools.pop(tool_id)
            logger.info("Tool unregistered: %s", removed.name)
            return Success(None)

    async def get_tool(self, tool_id: UUID) -> ToolMetadata | None:
        async with self._lock:
            return self._tools.get(tool_id)

    async def get_all_tools(self) -> list[ToolMetadata]:
        async with self._lock:
            return list(self._tools.values())

    async def find_tools_by_permission(self, permission: str) -> list[ToolMetadata]:
        async with self._lock:
            return [
                t for t in self._tools.values()
                if permission in t.permissions
            ]

    async def find_tools_by_name(self, name: str) -> list[ToolMetadata]:
        async with self._lock:
            name_lower = name.lower()
            return [t for t in self._tools.values() if name_lower in t.name.lower()]

    async def validate_tool_access(
        self, tool_id: UUID, agent_permissions: list[str],
    ) -> bool:
        async with self._lock:
            tool = self._tools.get(tool_id)
            if tool is None:
                return False
            if not tool.requires_authorization:
                return True
            return set(tool.permissions).issubset(set(agent_permissions))

    async def stats(self) -> dict[str, Any]:
        async with self._lock:
            return {
                "total_tools": len(self._tools),
                "tool_names": [t.name for t in self._tools.values()],
                "authorized_tools": sum(1 for t in self._tools.values() if t.requires_authorization),
                "unauthenticated_tools": sum(1 for t in self._tools.values() if not t.requires_authorization),
            }


def _digital_twin_query_tool() -> ToolMetadata:
    return ToolMetadata(
        tool_id=UUID("00000000-0000-0000-0000-0000000000a1"),
        name="Digital Twin Query",
        description="Query entity state, zone information, and venue data from the digital twin",
        schema={
            "type": "object",
            "properties": {
                "entity_id": {"type": "string", "format": "uuid"},
                "zone_id": {"type": "string", "format": "uuid"},
                "query_type": {"type": "string", "enum": ["entity_state", "zone_info", "venue_data"]},
            },
            "required": ["query_type"],
        },
        version="1.2.0",
        timeout_seconds=5.0,
        cache_ttl_seconds=30.0,
        max_retries=2,
        permissions=["read:digital_twin"],
    )


def _routing_engine_tool() -> ToolMetadata:
    return ToolMetadata(
        tool_id=UUID("00000000-0000-0000-0000-0000000000a2"),
        name="Routing Engine",
        description="Compute optimal routes and find paths through the venue graph",
        schema={
            "type": "object",
            "properties": {
                "origin": {"type": "string", "format": "uuid"},
                "destination": {"type": "string", "format": "uuid"},
                "algorithm": {"type": "string", "enum": ["dijkstra", "astar", "bfs"]},
                "accessibility_mode": {"type": "boolean", "default": False},
            },
            "required": ["origin", "destination"],
        },
        version="1.3.0",
        timeout_seconds=3.0,
        cache_ttl_seconds=60.0,
        max_retries=2,
        permissions=["read:venue", "read:crowd"],
    )


def _prediction_engine_tool() -> ToolMetadata:
    return ToolMetadata(
        tool_id=UUID("00000000-0000-0000-0000-0000000000a3"),
        name="Prediction Engine",
        description="Retrieve predictions and forecasts for crowd, weather, and incident trends",
        schema={
            "type": "object",
            "properties": {
                "prediction_type": {"type": "string"},
                "zone_id": {"type": "string", "format": "uuid"},
                "horizon_minutes": {"type": "integer", "minimum": 1, "maximum": 180},
                "min_confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            },
            "required": ["prediction_type"],
        },
        version="1.0.0",
        timeout_seconds=10.0,
        cache_ttl_seconds=120.0,
        max_retries=1,
        permissions=["read:sensors", "read:predictions"],
    )


def _knowledge_search_tool() -> ToolMetadata:
    return ToolMetadata(
        tool_id=UUID("00000000-0000-0000-0000-0000000000a4"),
        name="Knowledge Search",
        description="Search the knowledge base for SOPs, policies, and operational documents",
        schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "category": {"type": "string"},
                "max_results": {"type": "integer", "minimum": 1, "maximum": 20, "default": 5},
            },
            "required": ["query"],
        },
        version="1.0.0",
        timeout_seconds=8.0,
        cache_ttl_seconds=300.0,
        max_retries=2,
        permissions=["read:knowledge"],
    )


def _memory_search_tool() -> ToolMetadata:
    return ToolMetadata(
        tool_id=UUID("00000000-0000-0000-0000-0000000000a5"),
        name="Memory Search",
        description="Search conversational and operational memory for relevant context",
        schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "memory_type": {"type": "string", "enum": ["conversation", "operational", "semantic", "long_term"]},
                "session_id": {"type": "string", "format": "uuid"},
                "max_results": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10},
            },
            "required": ["query"],
        },
        version="1.0.0",
        timeout_seconds=5.0,
        cache_ttl_seconds=60.0,
        max_retries=2,
        permissions=["read:memory"],
    )


def _weather_service_tool() -> ToolMetadata:
    return ToolMetadata(
        tool_id=UUID("00000000-0000-0000-0000-0000000000a6"),
        name="Weather Service",
        description="Fetch current weather conditions and forecasts for the venue",
        schema={
            "type": "object",
            "properties": {
                "latitude": {"type": "number"},
                "longitude": {"type": "number"},
                "forecast_minutes": {"type": "integer", "minimum": 5, "maximum": 1440, "default": 60},
                "include_alerts": {"type": "boolean", "default": True},
            },
            "required": ["latitude", "longitude"],
        },
        version="1.0.0",
        timeout_seconds=8.0,
        cache_ttl_seconds=300.0,
        max_retries=3,
        permissions=["read:weather"],
    )


def _transit_service_tool() -> ToolMetadata:
    return ToolMetadata(
        tool_id=UUID("00000000-0000-0000-0000-0000000000a7"),
        name="Transit Service",
        description="Query transit schedules, parking availability, and shuttle status",
        schema={
            "type": "object",
            "properties": {
                "service_type": {"type": "string", "enum": ["transit", "parking", "shuttle"]},
                "zone_id": {"type": "string", "format": "uuid"},
                "time_window_minutes": {"type": "integer", "minimum": 5, "maximum": 360, "default": 60},
            },
            "required": ["service_type"],
        },
        version="1.0.0",
        timeout_seconds=6.0,
        cache_ttl_seconds=120.0,
        max_retries=2,
        permissions=["read:transit", "read:parking"],
    )


def _simulation_engine_tool() -> ToolMetadata:
    return ToolMetadata(
        tool_id=UUID("00000000-0000-0000-0000-0000000000a8"),
        name="Simulation Engine",
        description="Run what-if simulations and scenario analyses on the digital twin",
        schema={
            "type": "object",
            "properties": {
                "scenario": {"type": "string"},
                "parameters": {"type": "object"},
                "duration_minutes": {"type": "integer", "minimum": 1, "maximum": 180, "default": 30},
                "resolution_seconds": {"type": "integer", "minimum": 5, "maximum": 300, "default": 30},
            },
            "required": ["scenario"],
        },
        version="1.1.0",
        timeout_seconds=30.0,
        cache_ttl_seconds=0.0,
        max_retries=1,
        requires_authorization=True,
        permissions=["read:digital_twin", "write:simulation"],
    )


def _analytics_service_tool() -> ToolMetadata:
    return ToolMetadata(
        tool_id=UUID("00000000-0000-0000-0000-0000000000a9"),
        name="Analytics Service",
        description="Compute analytics, aggregate statistics, and generate operational reports",
        schema={
            "type": "object",
            "properties": {
                "metric": {"type": "string"},
                "zone_id": {"type": "string", "format": "uuid"},
                "start_time": {"type": "string", "format": "date-time"},
                "end_time": {"type": "string", "format": "date-time"},
                "granularity": {"type": "string", "enum": ["minute", "hour", "day"], "default": "hour"},
            },
            "required": ["metric"],
        },
        version="1.0.0",
        timeout_seconds=10.0,
        cache_ttl_seconds=180.0,
        max_retries=2,
        permissions=["read:sensors", "read:analytics"],
    )


def _incident_engine_tool() -> ToolMetadata:
    return ToolMetadata(
        tool_id=UUID("00000000-0000-0000-0000-0000000000b0"),
        name="Incident Engine",
        description="Report new incidents and query incident status and history",
        schema={
            "type": "object",
            "properties": {
                "operation": {"type": "string", "enum": ["report", "query", "update", "history"]},
                "incident_type": {"type": "string"},
                "zone_id": {"type": "string", "format": "uuid"},
                "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                "incident_id": {"type": "string", "format": "uuid"},
            },
            "required": ["operation"],
        },
        version="1.0.0",
        timeout_seconds=5.0,
        cache_ttl_seconds=0.0,
        max_retries=2,
        permissions=["read:incidents", "write:incidents"],
    )
