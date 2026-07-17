"""Dynamic agent registry — runtime registration and discovery of AI agents."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.features.orchestration.dto.agent import AgentCapability, AgentMetadata, RegisteredAgent
from app.features.orchestration.dto.request import AgentSelectorCriteria
from app.features.orchestration.models.enums import AgentStatus
from app.shared.result import Failure, Result, Success

logger = logging.getLogger(__name__)

StatusChangeCallback = Callable[[UUID, AgentStatus, AgentStatus], None]


@dataclass(frozen=True, slots=True)
class AgentLoadStats:
    current_load: int = 0
    total_invocations: int = 0
    total_errors: int = 0
    total_latency_ms: float = 0.0


class AgentRegistry:
    """In-memory, thread-safe registry for all AI agents."""

    def __init__(self) -> None:
        self._agents: dict[UUID, RegisteredAgent] = {}
        self._load_stats: dict[UUID, AgentLoadStats] = {}
        self._lock = asyncio.Lock()
        self._callbacks: list[StatusChangeCallback] = []
        self._register_default_agents()

    def _register_default_agents(self) -> None:
        defaults = [
            _crowd_intelligence_agent(),
            _navigation_agent(),
            _accessibility_agent(),
            _medical_agent(),
            _transport_agent(),
            _weather_agent(),
            _incident_agent(),
            _knowledge_agent(),
            _memory_agent(),
            _reasoning_agent(),
        ]
        for agent in defaults:
            self._agents[agent.metadata.agent_id] = agent
            self._load_stats[agent.metadata.agent_id] = AgentLoadStats()

    async def register_agent(self, metadata: AgentMetadata) -> Result[RegisteredAgent]:
        async with self._lock:
            if metadata.agent_id in self._agents:
                return Failure(
                    error_code="AGENT_ALREADY_REGISTERED",
                    message=f"Agent '{metadata.agent_id}' already exists",
                )

            registered = RegisteredAgent(
                metadata=metadata,
                status=AgentStatus.AVAILABLE,
                health_score=1.0,
                last_heartbeat=datetime.now(UTC),
            )
            self._agents[metadata.agent_id] = registered
            self._load_stats[metadata.agent_id] = AgentLoadStats()
            logger.info("Agent registered: %s (%s)", metadata.name, metadata.agent_id)
            return Success(registered)

    async def unregister_agent(self, agent_id: UUID) -> Result[None]:
        async with self._lock:
            if agent_id not in self._agents:
                return Failure(
                    error_code="AGENT_NOT_FOUND",
                    message=f"Agent '{agent_id}' not found",
                )
            removed = self._agents.pop(agent_id)
            self._load_stats.pop(agent_id, None)
            logger.info("Agent unregistered: %s", removed.metadata.name)
            return Success(None)

    async def get_agent(self, agent_id: UUID) -> Result[RegisteredAgent | None]:
        async with self._lock:
            return Success(self._agents.get(agent_id))

    async def get_all_agents(self) -> list[RegisteredAgent]:
        async with self._lock:
            return list(self._agents.values())

    async def find_agents(self, criteria: AgentSelectorCriteria) -> list[RegisteredAgent]:
        async with self._lock:
            results: list[RegisteredAgent] = []
            for agent in self._agents.values():
                if agent.status not in (AgentStatus.AVAILABLE, AgentStatus.BUSY):
                    continue
                if agent.health_score <= 0.5:
                    continue
                if criteria.excluded_agents and agent.metadata.agent_id in criteria.excluded_agents:
                    continue
                if criteria.preferred_agents and agent.metadata.agent_id not in criteria.preferred_agents:
                    continue
                if criteria.required_capabilities:
                    agent_caps = {c.name for c in agent.metadata.capabilities}
                    if not set(criteria.required_capabilities).issubset(agent_caps):
                        continue
                if criteria.max_cost is not None and agent.metadata.cost_per_invocation > criteria.max_cost:
                    continue
                if criteria.max_latency_ms is not None and agent.metadata.avg_latency_ms > criteria.max_latency_ms:
                    continue
                if agent.current_load >= agent.metadata.max_concurrent:
                    continue
                results.append(agent)
            return results

    async def update_agent_status(self, agent_id: UUID, status: AgentStatus) -> Result[None]:
        async with self._lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                return Failure(
                    error_code="AGENT_NOT_FOUND",
                    message=f"Agent '{agent_id}' not found",
                )
            old_status = agent.status
            updated = agent.model_copy(update={"status": status, "last_heartbeat": datetime.now(UTC)})
            self._agents[agent_id] = updated
            for callback in self._callbacks:
                callback(agent_id, old_status, status)
            return Success(None)

    async def update_agent_health(self, agent_id: UUID, health_score: float) -> Result[None]:
        async with self._lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                return Failure(
                    error_code="AGENT_NOT_FOUND",
                    message=f"Agent '{agent_id}' not found",
                )
            clamped = max(0.0, min(1.0, health_score))
            updated = agent.model_copy(update={"health_score": clamped, "last_heartbeat": datetime.now(UTC)})
            self._agents[agent_id] = updated
            return Success(None)

    async def record_invocation(self, agent_id: UUID) -> Result[None]:
        async with self._lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                return Failure(
                    error_code="AGENT_NOT_FOUND",
                    message=f"Agent '{agent_id}' not found",
                )
            new_load = agent.current_load + 1
            updated = agent.model_copy(update={"current_load": new_load})
            self._agents[agent_id] = updated

            stats = self._load_stats.get(agent_id, AgentLoadStats())
            self._load_stats[agent_id] = AgentLoadStats(
                current_load=new_load,
                total_invocations=stats.total_invocations + 1,
                total_errors=stats.total_errors,
                total_latency_ms=stats.total_latency_ms,
            )
            if new_load >= agent.metadata.max_concurrent:
                await self.update_agent_status(agent_id, AgentStatus.BUSY)
            return Success(None)

    async def record_completion(
        self, agent_id: UUID, success: bool, latency_ms: float,
    ) -> Result[None]:
        async with self._lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                return Failure(
                    error_code="AGENT_NOT_FOUND",
                    message=f"Agent '{agent_id}' not found",
                )
            new_load = max(0, agent.current_load - 1)
            stats = self._load_stats.get(agent_id, AgentLoadStats())
            new_errors = stats.total_errors + (0 if success else 1)
            new_latency = stats.total_latency_ms + latency_ms
            new_invocations = stats.total_invocations

            new_error_rate = new_errors / new_invocations if new_invocations > 0 else 0.0
            updated = agent.model_copy(update={
                "current_load": new_load,
                "error_rate": new_error_rate,
            })
            self._agents[agent_id] = updated
            self._load_stats[agent_id] = AgentLoadStats(
                current_load=new_load,
                total_invocations=new_invocations,
                total_errors=new_errors,
                total_latency_ms=new_latency,
            )

            if new_load < agent.metadata.max_concurrent and agent.status == AgentStatus.BUSY:
                await self.update_agent_status(agent_id, AgentStatus.AVAILABLE)
            return Success(None)

    async def get_healthy_agents(self) -> list[RegisteredAgent]:
        async with self._lock:
            return [
                a for a in self._agents.values()
                if a.health_score > 0.5 and a.status in (AgentStatus.AVAILABLE, AgentStatus.BUSY)
            ]

    async def get_agents_for_action(self, action: str) -> list[RegisteredAgent]:
        async with self._lock:
            return [
                a for a in self._agents.values()
                if action in a.metadata.supported_actions
                and a.status in (AgentStatus.AVAILABLE, AgentStatus.BUSY)
            ]

    def on_agent_status_change(self, callback: StatusChangeCallback) -> None:
        self._callbacks.append(callback)

    async def stats(self) -> dict[str, Any]:
        async with self._lock:
            status_counts: dict[str, int] = {}
            total_health = 0.0
            for agent in self._agents.values():
                key = agent.status.value
                status_counts[key] = status_counts.get(key, 0) + 1
                total_health += agent.health_score

            return {
                "total_agents": len(self._agents),
                "status_distribution": status_counts,
                "avg_health": total_health / len(self._agents) if self._agents else 0.0,
                "total_load": sum(a.current_load for a in self._agents.values()),
            }


def _capability(name: str, description: str) -> AgentCapability:
    return AgentCapability(name=name, description=description)


def _make_agent(
    agent_id: UUID,
    name: str,
    description: str,
    capabilities: list[AgentCapability],
    actions: list[str],
    cost: float,
    latency: float,
    priority: int,
    permissions: list[str],
    tools: list[UUID],
    max_concurrent: int = 10,
    version: str = "1.0.0",
) -> RegisteredAgent:
    metadata = AgentMetadata(
        agent_id=agent_id,
        name=name,
        description=description,
        capabilities=capabilities,
        supported_actions=actions,
        cost_per_invocation=cost,
        avg_latency_ms=latency,
        priority=priority,
        version=version,
        permissions=permissions,
        supported_tools=tools,
        max_concurrent=max_concurrent,
    )
    return RegisteredAgent(metadata=metadata, status=AgentStatus.AVAILABLE, health_score=1.0)


def _crowd_intelligence_agent() -> RegisteredAgent:
    return _make_agent(
        agent_id=UUID("00000000-0000-0000-0000-000000000001"),
        name="Crowd Intelligence Agent",
        description="Monitors crowd density, flow patterns, and detects bottlenecks in real time",
        capabilities=[
            _capability("crowd_management", "Analyze and manage crowd flow dynamics"),
            _capability("density_analysis", "Compute real-time crowd density metrics per zone"),
            _capability("bottleneck_detection", "Identify emerging congestion points before saturation"),
        ],
        actions=["crowd_management", "density_analysis", "bottleneck_detection"],
        cost=0.05,
        latency=150.0,
        priority=8,
        permissions=["read:sensors", "read:crowd", "write:alerts"],
        tools=[],
        max_concurrent=20,
        version="1.2.0",
    )


def _navigation_agent() -> RegisteredAgent:
    return _make_agent(
        agent_id=UUID("00000000-0000-0000-0000-000000000002"),
        name="Navigation Agent",
        description="Provides optimal routing and pathfinding for spectators and staff",
        capabilities=[
            _capability("routing", "Compute shortest and fastest routes through the venue"),
            _capability("pathfinding", "Navigate complex multi-level stadium graph structures"),
            _capability("rerouting", "Dynamically reroute when corridors are blocked or congested"),
            _capability("accessibility_routing", "Route with accessibility constraints such as ramps and elevators"),
        ],
        actions=["routing", "pathfinding", "rerouting", "accessibility_routing"],
        cost=0.03,
        latency=80.0,
        priority=9,
        permissions=["read:venue", "read:crowd", "read:sensors"],
        tools=[],
        max_concurrent=50,
        version="1.3.1",
    )


def _accessibility_agent() -> RegisteredAgent:
    return _make_agent(
        agent_id=UUID("00000000-0000-0000-0000-000000000003"),
        name="Accessibility Agent",
        description="Ensures inclusive access for disabled spectators and staff",
        capabilities=[
            _capability("wheelchair_access", "Plan wheelchair-accessible routes and seating"),
            _capability("visual_impairment", "Provide audio-described and tactile guidance"),
            _capability("accessibility_routing", "Optimize routes for mobility-impaired individuals"),
            _capability("accessibility_assessment", "Evaluate zone accessibility compliance in real time"),
        ],
        actions=["wheelchair_access", "visual_impairment", "accessibility_routing", "accessibility_assessment"],
        cost=0.04,
        latency=120.0,
        priority=10,
        permissions=["read:venue", "read:crowd", "write:accessibility"],
        tools=[],
        max_concurrent=30,
        version="1.1.0",
    )


def _medical_agent() -> RegisteredAgent:
    return _make_agent(
        agent_id=UUID("00000000-0000-0000-0000-000000000004"),
        name="Medical Agent",
        description="Coordinates medical response, triage, and emergency healthcare dispatch",
        capabilities=[
            _capability("medical_response", "Dispatch medical teams to incident locations"),
            _capability("first_aid", "Provide step-by-step first-aid guidance to volunteers"),
            _capability("triage", "Classify patient severity and prioritize treatment"),
            _capability("emergency_medical", "Coordinate mass-casualty medical escalation"),
        ],
        actions=["medical_response", "first_aid", "triage", "emergency_medical"],
        cost=0.08,
        latency=200.0,
        priority=10,
        permissions=["read:sensors", "read:crowd", "write:incidents", "read:medical"],
        tools=[],
        max_concurrent=5,
        version="1.0.0",
    )


def _transport_agent() -> RegisteredAgent:
    return _make_agent(
        agent_id=UUID("00000000-0000-0000-0000-000000000005"),
        name="Transport Agent",
        description="Manages transit schedules, parking, shuttles, and evacuation transport",
        capabilities=[
            _capability("transit_management", "Coordinate public transit and shuttle schedules"),
            _capability("parking", "Optimize parking allocation and guide vehicles"),
            _capability("shuttle", "Schedule and dispatch shuttles for spectators"),
            _capability("evacuation_transport", "Organize transport assets for emergency evacuation"),
        ],
        actions=["transit_management", "parking", "shuttle", "evacuation_transport"],
        cost=0.06,
        latency=250.0,
        priority=7,
        permissions=["read:transit", "read:parking", "write:transit"],
        tools=[],
        max_concurrent=10,
        version="1.0.0",
    )


def _weather_agent() -> RegisteredAgent:
    return _make_agent(
        agent_id=UUID("00000000-0000-0000-0000-000000000006"),
        name="Weather Agent",
        description="Monitors weather conditions and issues venue-specific advisories",
        capabilities=[
            _capability("weather_monitoring", "Track real-time weather at and around the venue"),
            _capability("weather_advisory", "Generate actionable weather advisories for operations"),
            _capability("severe_weather", "Detect and escalate severe weather alerts"),
        ],
        actions=["weather_monitoring", "weather_advisory", "severe_weather"],
        cost=0.02,
        latency=100.0,
        priority=8,
        permissions=["read:weather", "write:alerts"],
        tools=[],
        max_concurrent=5,
        version="1.0.0",
    )


def _incident_agent() -> RegisteredAgent:
    return _make_agent(
        agent_id=UUID("00000000-0000-0000-0000-000000000007"),
        name="Incident Agent",
        description="Detects, classifies, and escalates operational incidents",
        capabilities=[
            _capability("incident_detection", "Identify incidents from sensor and event data"),
            _capability("incident_response", "Coordinate initial response actions"),
            _capability("incident_escalation", "Escalate incidents to appropriate authority levels"),
        ],
        actions=["incident_detection", "incident_response", "incident_escalation"],
        cost=0.07,
        latency=180.0,
        priority=9,
        permissions=["read:sensors", "read:crowd", "write:incidents"],
        tools=[],
        max_concurrent=15,
        version="1.1.0",
    )


def _knowledge_agent() -> RegisteredAgent:
    return _make_agent(
        agent_id=UUID("00000000-0000-0000-0000-000000000008"),
        name="Knowledge Agent",
        description="Retrieves relevant SOPs, policies, and operational documents",
        capabilities=[
            _capability("knowledge_search", "Search the knowledge base for relevant information"),
            _capability("document_retrieval", "Fetch specific operational documents and policies"),
            _capability("sop_lookup", "Look up standard operating procedures for scenarios"),
        ],
        actions=["knowledge_search", "document_retrieval", "sop_lookup"],
        cost=0.01,
        latency=200.0,
        priority=6,
        permissions=["read:knowledge"],
        tools=[],
        max_concurrent=30,
        version="1.0.0",
    )


def _memory_agent() -> RegisteredAgent:
    return _make_agent(
        agent_id=UUID("00000000-0000-0000-0000-000000000009"),
        name="Memory Agent",
        description="Manages short-term and long-term memory for context-aware reasoning",
        capabilities=[
            _capability("memory_retrieval", "Retrieve relevant past interactions and context"),
            _capability("context_summarization", "Summarize conversation and event history"),
            _capability("conversation_history", "Maintain and query multi-turn conversation state"),
        ],
        actions=["memory_retrieval", "context_summarization", "conversation_history"],
        cost=0.02,
        latency=150.0,
        priority=5,
        permissions=["read:memory", "write:memory"],
        tools=[],
        max_concurrent=20,
        version="1.0.0",
    )


def _reasoning_agent() -> RegisteredAgent:
    return _make_agent(
        agent_id=UUID("00000000-0000-0000-0000-00000000000a"),
        name="Reasoning Agent",
        description="Performs multi-step reasoning, causal analysis, and strategic planning",
        capabilities=[
            _capability("multi_step_reasoning", "Chain logical inferences across multiple data sources"),
            _capability("causal_analysis", "Determine root causes from correlated events"),
            _capability("strategic_planning", "Generate multi-phase action plans for complex scenarios"),
        ],
        actions=["multi_step_reasoning", "causal_analysis", "strategic_planning"],
        cost=0.10,
        latency=500.0,
        priority=7,
        permissions=["read:sensors", "read:crowd", "read:memory", "read:knowledge"],
        tools=[],
        max_concurrent=5,
        version="1.0.0",
    )
