"""Monitoring and observability API routes — metrics, graphs, health, and tools."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.features.orchestration.api.deps import (
    get_agent_registry,
    get_metrics,
    get_tool_registry,
)
from app.features.orchestration.observability.metrics import OrchestrationMetrics
from app.features.orchestration.registry.agent_registry import AgentRegistry
from app.features.orchestration.registry.tool_registry import ToolRegistry

router = APIRouter(prefix="/orchestration", tags=["Monitoring & Observability"])


@router.get(
    "/monitoring/metrics",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Get metrics summary",
    description=(
        "Retrieve aggregated orchestration metrics including "
        "latencies, success rates, and confidence."
    ),
)
async def get_metrics_summary(
    metrics: OrchestrationMetrics = Depends(get_metrics),
) -> dict:
    summary = metrics.get_metrics_summary()
    return {
        "total_executions": summary.total_executions,
        "active_executions": summary.active_executions,
        "avg_duration_ms": summary.avg_duration_ms,
        "p50_duration_ms": summary.p50_duration_ms,
        "p95_duration_ms": summary.p95_duration_ms,
        "p99_duration_ms": summary.p99_duration_ms,
        "success_rate": summary.success_rate,
        "error_rate": summary.error_rate,
        "total_agent_invocations": summary.total_agent_invocations,
        "agent_invocations_by_type": summary.agent_invocations_by_type,
        "avg_confidence": summary.avg_confidence,
        "safety_violations_total": summary.safety_violations_total,
        "conflicts_resolved": summary.conflicts_resolved,
        "cache_hit_rate": summary.cache_hit_rate,
    }


@router.get(
    "/monitoring/graph/{execution_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Get execution graph",
    description="Retrieve the step-level execution graph for a specific execution.",
)
async def get_execution_graph(
    execution_id: UUID,
    metrics: OrchestrationMetrics = Depends(get_metrics),
) -> dict:
    graph = metrics.get_execution_graph(execution_id)
    if "error" in graph:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=graph["error"],
        )
    return graph


@router.get(
    "/monitoring/health",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="System health check",
    description="Check the overall health of the orchestration engine subsystems.",
)
async def get_system_health(
    agent_registry: AgentRegistry = Depends(get_agent_registry),
    tool_registry: ToolRegistry = Depends(get_tool_registry),
    metrics: OrchestrationMetrics = Depends(get_metrics),
) -> dict:
    agent_stats = await agent_registry.stats()
    tool_stats = await tool_registry.stats()
    metrics_summary = metrics.get_metrics_summary()

    health_indicators: dict[str, str] = {}
    if agent_stats["avg_health"] < 0.5:
        health_indicators["agents"] = "degraded"
    else:
        health_indicators["agents"] = "healthy"

    if metrics_summary.error_rate > 0.2:
        health_indicators["execution"] = "degraded"
    else:
        health_indicators["execution"] = "healthy"

    overall = "healthy"
    if any(v != "healthy" for v in health_indicators.values()):
        overall = "degraded"

    return {
        "status": overall,
        "agents": agent_stats,
        "tools": tool_stats,
        "execution_health": health_indicators,
        "metrics_summary": {
            "total_executions": metrics_summary.total_executions,
            "success_rate": metrics_summary.success_rate,
            "avg_confidence": metrics_summary.avg_confidence,
        },
    }


@router.get(
    "/tools",
    response_model=list[dict],
    status_code=status.HTTP_200_OK,
    summary="List all registered tools",
    description="Retrieve all tools currently registered in the orchestration tool registry.",
)
async def list_tools(
    tool_registry: ToolRegistry = Depends(get_tool_registry),
) -> list[dict]:
    tools = await tool_registry.get_all_tools()
    return [
        {
            "tool_id": str(t.tool_id),
            "name": t.name,
            "description": t.description,
            "version": t.version,
            "timeout_seconds": t.timeout_seconds,
            "cache_ttl_seconds": t.cache_ttl_seconds,
            "max_retries": t.max_retries,
            "requires_authorization": t.requires_authorization,
            "permissions": t.permissions,
        }
        for t in tools
    ]
