from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from typing import Any, Protocol
from uuid import UUID, uuid4

from app.features.orchestration.dto.tool import ToolInvocationResult, ToolMetadata
from app.shared.result import Failure, Result, Success

logging = logging.getLogger(__name__)


class ToolRegistry(Protocol):
    def get_tool(self, tool_id: UUID) -> ToolMetadata | None: ...
    def validate_tool_access(self, tool_id: UUID, permissions: list[str]) -> Result[None]: ...


class ToolExecutor:
    def __init__(
        self,
        tool_registry: ToolRegistry,
        observability: Any | None = None,
    ) -> None:
        self._registry = tool_registry
        self._observability = observability
        self._cache: dict[str, tuple[dict, float]] = {}

    async def execute(
        self,
        tool_id: UUID,
        parameters: dict,
        agent_permissions: list[str],
        timeout_seconds: float = 10.0,
    ) -> Result[ToolInvocationResult]:
        tool = self._registry.get_tool(tool_id)
        if tool is None:
            return Failure(
                error_code="TOOL_NOT_FOUND",
                message=f"Tool {tool_id} not found in registry",
            )

        access_check = self._registry.validate_tool_access(tool_id, agent_permissions)
        if isinstance(access_check, Failure):
            return Failure(
                error_code="TOOL_ACCESS_DENIED",
                message=f"Agent lacks permission for tool {tool.name}",
                details={"tool_id": str(tool_id), "required_permissions": tool.permissions},
            )

        validation = self._validate_parameters(tool, parameters)
        if isinstance(validation, Failure):
            return Failure(
                error_code="TOOL_VALIDATION_FAILED",
                message=f"Parameter validation failed for tool {tool.name}",
                details={"tool_id": str(tool_id), "validation_errors": validation.details},
            )

        effective_timeout = min(timeout_seconds, tool.timeout_seconds)
        cache_key = self._get_cache_key(tool_id, parameters)

        if tool.cache_ttl_seconds > 0:
            cached = self._check_cache(cache_key, tool.cache_ttl_seconds)
            if cached is not None:
                result = ToolInvocationResult(
                    tool_id=tool_id,
                    success=True,
                    result=cached,
                    duration_ms=0.0,
                    cache_hit=True,
                )
                logging.info("Cache hit for tool %s", tool.name)
                return Success(value=result)

        start_time = time.monotonic()
        last_error: str | None = None
        max_attempts = tool.max_retries + 1

        for attempt in range(max_attempts):
            try:
                raw_result = await asyncio.wait_for(
                    self._execute_tool(tool, parameters),
                    timeout=effective_timeout,
                )
                duration_ms = (time.monotonic() - start_time) * 1000

                if tool.cache_ttl_seconds > 0:
                    self._set_cache(cache_key, raw_result, tool.cache_ttl_seconds)

                invocation_result = ToolInvocationResult(
                    tool_id=tool_id,
                    success=True,
                    result=raw_result,
                    duration_ms=duration_ms,
                    cache_hit=False,
                )

                if self._observability is not None:
                    self._observability.record_tool_call(
                        tool_id=tool_id,
                        tool_name=tool.name,
                        parameters=parameters,
                        result=raw_result,
                        success=True,
                        duration_ms=duration_ms,
                        cache_hit=False,
                    )

                return Success(value=invocation_result)

            except TimeoutError:
                last_error = (
                    f"Tool {tool.name} timed out after"
                    f" {effective_timeout}s on attempt"
                    f" {attempt + 1}"
                )
                logging.warning(last_error)

            except Exception as exc:
                last_error = f"Tool {tool.name} failed: {exc}"
                logging.warning(last_error)

            if attempt < max_attempts - 1:
                await asyncio.sleep(0.1 * (2 ** attempt))

        duration_ms = (time.monotonic() - start_time) * 1000
        failure_result = ToolInvocationResult(
            tool_id=tool_id,
            success=False,
            error=last_error or "Unknown error",
            duration_ms=duration_ms,
            cache_hit=False,
        )

        if self._observability is not None:
            self._observability.record_tool_call(
                tool_id=tool_id,
                tool_name=tool.name,
                parameters=parameters,
                result=None,
                success=False,
                duration_ms=duration_ms,
                cache_hit=False,
            )

        return Success(value=failure_result)

    async def _execute_tool(self, tool: ToolMetadata, parameters: dict) -> dict:
        name_lower = tool.name.lower()

        if "digital twin" in name_lower or "entity" in name_lower:
            return {
                "entity_id": parameters.get("entity_id", str(uuid4())),
                "zone": parameters.get("zone", "Zone A"),
                "capacity": 50000,
                "current_occupancy": 32450,
                "occupancy_rate": 0.649,
                "temperature_celsius": 28.5,
                "air_quality_index": 42,
                "sensor_readings": {
                    "crowd_density": 0.65,
                    "noise_level_db": 78.2,
                    "vibration": 0.02,
                },
                "status": "operational",
                "last_updated": "2026-07-16T14:30:00Z",
            }

        if "routing" in name_lower or "route" in name_lower:
            return {
                "route_id": str(uuid4()),
                "origin": parameters.get("origin", "Gate A1"),
                "destination": parameters.get("destination", "Section 105"),
                "distance_meters": 340.5,
                "estimated_duration_seconds": 420,
                "accessibility_compliant": True,
                "elevator_available": True,
                "crowd_level": "moderate",
                "waypoints": [
                    {"lat": 38.8977, "lng": -77.0365, "label": "Concourse Level"},
                    {"lat": 38.8979, "lng": -77.0362, "label": "Section 105 Entrance"},
                ],
                "alternative_routes": 2,
                "safety_score": 0.95,
            }

        if "knowledge" in name_lower or "search" in name_lower:
            return {
                "query": parameters.get("query", ""),
                "results_count": 3,
                "results": [
                    {
                        "document_id": str(uuid4()),
                        "title": "FIFA World Cup 2026 Crowd Management SOP",
                        "category": "safety_sop",
                        "relevance_score": 0.92,
                        "excerpt": "Section 4.2: When crowd density exceeds 85% capacity...",
                    },
                    {
                        "document_id": str(uuid4()),
                        "title": "Volunteer Emergency Response Guide",
                        "category": "volunteer_manual",
                        "relevance_score": 0.87,
                        "excerpt": "In case of medical emergency, first notify dispatch...",
                    },
                    {
                        "document_id": str(uuid4()),
                        "title": "Stadium Evacuation Procedures",
                        "category": "emergency_procedure",
                        "relevance_score": 0.81,
                        "excerpt": "Evacuation triggers include fire alarm activation...",
                    },
                ],
                "search_time_ms": 12.4,
                "index_version": "2026.07",
            }

        if "weather" in name_lower:
            return {
                "location": parameters.get("venue", "Stadium"),
                "conditions": "partly_cloudy",
                "temperature_celsius": 31.2,
                "feels_like_celsius": 34.8,
                "humidity_percent": 68,
                "wind_speed_kmh": 14.5,
                "wind_direction": "SW",
                "precipitation_probability": 0.15,
                "uv_index": 8,
                "heat_advisory": True,
                "forecast": [
                    {"hour": 18, "temp": 29.0, "conditions": "clear"},
                    {"hour": 20, "temp": 26.5, "conditions": "partly_cloudy"},
                    {"hour": 22, "temp": 23.0, "conditions": "clear"},
                ],
                "alerts": [
                    {
                        "type": "heat_advisory",
                        "severity": "moderate",
                        "message": (
                            "Heat index expected to exceed 35C."
                            " Ensure hydration stations"
                            " are stocked."
                        ),
                    },
                ],
            }

        return {
            "tool_name": tool.name,
            "parameters_received": parameters,
            "status": "completed",
            "timestamp": time.time(),
        }

    def _validate_parameters(self, tool: ToolMetadata, parameters: dict) -> Result[None]:
        schema = tool.schema
        if not schema:
            return Success(value=None)

        required_fields = schema.get("required", [])
        for field_name in required_fields:
            if field_name not in parameters:
                return Failure(
                    error_code="MISSING_PARAMETER",
                    message=f"Required parameter '{field_name}' is missing",
                    details={"required": required_fields, "provided": list(parameters.keys())},
                )

        properties = schema.get("properties", {})
        for key, value in parameters.items():
            if key in properties:
                expected_type = properties[key].get("type")
                if expected_type == "string" and not isinstance(value, str):
                    return Failure(
                        error_code="INVALID_PARAMETER_TYPE",
                        message=f"Parameter '{key}' must be a string",
                    )
                if expected_type == "integer" and not isinstance(value, int):
                    return Failure(
                        error_code="INVALID_PARAMETER_TYPE",
                        message=f"Parameter '{key}' must be an integer",
                    )
                if expected_type == "number" and not isinstance(value, (int, float)):
                    return Failure(
                        error_code="INVALID_PARAMETER_TYPE",
                        message=f"Parameter '{key}' must be a number",
                    )
                if expected_type == "boolean" and not isinstance(value, bool):
                    return Failure(
                        error_code="INVALID_PARAMETER_TYPE",
                        message=f"Parameter '{key}' must be a boolean",
                    )

        return Success(value=None)

    def _get_cache_key(self, tool_id: UUID, parameters: dict) -> str:
        canonical = json.dumps(
            {"tool_id": str(tool_id), "params": parameters},
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(canonical.encode()).hexdigest()

    def _check_cache(self, key: str, ttl: float) -> dict | None:
        if key in self._cache:
            value, stored_at = self._cache[key]
            if (time.monotonic() - stored_at) < ttl:
                return value
            del self._cache[key]
        return None

    def _set_cache(self, key: str, value: dict, ttl: float) -> None:
        self._cache[key] = (value, time.monotonic())
