"""Agent management API routes — list, inspect, update, and health-check agents."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.features.orchestration.api.deps import get_agent_registry
from app.features.orchestration.models.enums import AgentStatus
from app.features.orchestration.registry.agent_registry import AgentRegistry
from app.shared.result import Success

router = APIRouter(prefix="/orchestration/agents", tags=["Agent Management"])


@router.get(
    "",
    response_model=list[dict],
    status_code=status.HTTP_200_OK,
    summary="List all agents",
    description="Retrieve all registered agents with their current status.",
)
async def list_agents(
    registry: AgentRegistry = Depends(get_agent_registry),
) -> list[dict]:
    agents = await registry.get_all_agents()
    return [
        {
            "agent_id": str(a.metadata.agent_id),
            "name": a.metadata.name,
            "description": a.metadata.description,
            "status": a.status.value,
            "capabilities": [c.name for c in a.metadata.capabilities],
            "current_load": a.current_load,
            "health_score": a.health_score,
            "priority": a.metadata.priority,
            "version": a.metadata.version,
            "cost_per_invocation": a.metadata.cost_per_invocation,
            "avg_latency_ms": a.metadata.avg_latency_ms,
            "max_concurrent": a.metadata.max_concurrent,
        }
        for a in agents
    ]


@router.get(
    "/status",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Get agent statuses",
    description="Retrieve a summary of agent statuses and distribution.",
)
async def get_agent_statuses(
    registry: AgentRegistry = Depends(get_agent_registry),
) -> dict:
    agents = await registry.get_all_agents()
    status_counts: dict[str, int] = {}
    for agent in agents:
        key = agent.status.value
        status_counts[key] = status_counts.get(key, 0) + 1

    return {
        "total_agents": len(agents),
        "status_distribution": status_counts,
        "agents": [
            {
                "agent_id": str(a.metadata.agent_id),
                "name": a.metadata.name,
                "status": a.status.value,
                "health_score": a.health_score,
                "current_load": a.current_load,
            }
            for a in agents
        ],
    }


@router.get(
    "/health",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Get agent health summary",
    description="Retrieve health statistics across all registered agents.",
)
async def get_agent_health(
    registry: AgentRegistry = Depends(get_agent_registry),
) -> dict:
    stats = await registry.stats()
    healthy_agents = await registry.get_healthy_agents()

    return {
        **stats,
        "healthy_count": len(healthy_agents),
        "unhealthy_agents": [
            {
                "agent_id": str(a.metadata.agent_id),
                "name": a.metadata.name,
                "health_score": a.health_score,
                "status": a.status.value,
            }
            for a in (await registry.get_all_agents())
            if a.health_score <= 0.5
        ],
    }


@router.get(
    "/{agent_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Get agent details",
    description="Retrieve detailed information about a specific agent.",
)
async def get_agent(
    agent_id: UUID,
    registry: AgentRegistry = Depends(get_agent_registry),
) -> dict:
    result = await registry.get_agent(agent_id)
    if not isinstance(result, Success):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve agent",
        )
    agent = result.value
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found",
        )

    return {
        "agent_id": str(agent.metadata.agent_id),
        "name": agent.metadata.name,
        "description": agent.metadata.description,
        "status": agent.status.value,
        "capabilities": [
            {
                "name": c.name,
                "description": c.description,
            }
            for c in agent.metadata.capabilities
        ],
        "supported_actions": agent.metadata.supported_actions,
        "permissions": agent.metadata.permissions,
        "current_load": agent.current_load,
        "health_score": agent.health_score,
        "error_rate": agent.error_rate,
        "priority": agent.metadata.priority,
        "version": agent.metadata.version,
        "cost_per_invocation": agent.metadata.cost_per_invocation,
        "avg_latency_ms": agent.metadata.avg_latency_ms,
        "max_concurrent": agent.metadata.max_concurrent,
        "last_heartbeat": (
            agent.last_heartbeat.isoformat() if agent.last_heartbeat else None
        ),
    }


@router.put(
    "/{agent_id}/status",
    status_code=status.HTTP_200_OK,
    summary="Update agent status",
    description="Manually update the operational status of a registered agent.",
)
async def update_agent_status(
    agent_id: UUID,
    new_status: AgentStatus = Query(..., description="New status for the agent"),
    registry: AgentRegistry = Depends(get_agent_registry),
) -> dict:
    result = await registry.update_agent_status(agent_id, new_status)
    if not isinstance(result, Success):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=result.message,
        )
    return {
        "agent_id": str(agent_id),
        "status": new_status.value,
        "message": f"Agent status updated to {new_status.value}",
    }
