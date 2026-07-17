"""Tests for ConflictResolver — multi-agent output conflict detection and resolution strategies."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from app.features.orchestration.collaboration.conflict_resolver import ConflictResolver
from app.features.orchestration.dto.agent import AgentCapability, AgentMetadata, RegisteredAgent
from app.features.orchestration.models.enums import AgentStatus, ConflictResolutionStrategy
from app.shared.result import Success


def _make_agent(
    agent_id: UUID,
    name: str,
    priority: int = 5,
) -> RegisteredAgent:
    return RegisteredAgent(
        metadata=AgentMetadata(
            agent_id=agent_id,
            name=name,
            description=f"{name} desc",
            capabilities=[AgentCapability(name="general", description="general")],
            supported_actions=["general"],
            cost_per_invocation=0.05,
            avg_latency_ms=100.0,
            priority=priority,
            version="1.0.0",
            permissions=[],
            supported_tools=[],
        ),
        status=AgentStatus.AVAILABLE,
        health_score=1.0,
    )


@pytest.fixture
def agent_a_id() -> UUID:
    return uuid4()


@pytest.fixture
def agent_b_id() -> UUID:
    return uuid4()


@pytest.fixture
def agent_c_id() -> UUID:
    return uuid4()


class TestConflictResolver:

    @pytest.mark.asyncio
    async def test_resolve_no_conflict(self, agent_a_id: UUID, agent_b_id: UUID) -> None:
        resolver = ConflictResolver()
        outputs = {
            agent_a_id: {"recommendation": "open gate A", "confidence": 0.9},
            agent_b_id: {"evidence": [{"type": "sensor", "description": "gate A clear"}]},
        }
        agents = [
            _make_agent(agent_a_id, "Agent A"),
            _make_agent(agent_b_id, "Agent B"),
        ]
        result = await resolver.resolve(outputs, agents)
        assert isinstance(result, Success)
        assert result.value["recommendation"] == "open gate A"

    @pytest.mark.asyncio
    async def test_resolve_single_output(self, agent_a_id: UUID) -> None:
        resolver = ConflictResolver()
        outputs = {agent_a_id: {"recommendation": "do X", "confidence": 0.8}}
        agents = [_make_agent(agent_a_id, "Agent A")]
        result = await resolver.resolve(outputs, agents)
        assert isinstance(result, Success)
        assert result.value["recommendation"] == "do X"

    @pytest.mark.asyncio
    async def test_resolve_empty_outputs(self) -> None:
        resolver = ConflictResolver()
        result = await resolver.resolve({}, [])
        assert isinstance(result, Success)
        assert result.value == {}

    @pytest.mark.asyncio
    async def test_resolve_priority_based(
        self, agent_a_id: UUID, agent_b_id: UUID,
    ) -> None:
        resolver = ConflictResolver(strategy=ConflictResolutionStrategy.PRIORITY_BASED)
        outputs = {
            agent_a_id: {"recommendation": "close gate A", "confidence": 0.9},
            agent_b_id: {"recommendation": "open gate A", "confidence": 0.8},
        }
        agents = [
            _make_agent(agent_a_id, "Agent A", priority=3),
            _make_agent(agent_b_id, "Agent B", priority=9),
        ]
        result = await resolver.resolve(outputs, agents)
        assert isinstance(result, Success)
        assert result.value["recommendation"] == "open gate A"
        assert "_conflict_resolution" in result.value
        assert result.value["_conflict_resolution"]["strategy"] == "priority_based"

    @pytest.mark.asyncio
    async def test_resolve_confidence_based(
        self, agent_a_id: UUID, agent_b_id: UUID,
    ) -> None:
        resolver = ConflictResolver(strategy=ConflictResolutionStrategy.CONFIDENCE_BASED)
        outputs = {
            agent_a_id: {"recommendation": "low conf rec", "confidence": 0.4},
            agent_b_id: {"recommendation": "high conf rec", "confidence": 0.95},
        }
        agents = [
            _make_agent(agent_a_id, "Agent A"),
            _make_agent(agent_b_id, "Agent B"),
        ]
        result = await resolver.resolve(outputs, agents)
        assert isinstance(result, Success)
        assert result.value["recommendation"] == "high conf rec"
        assert result.value["_conflict_resolution"]["strategy"] == "confidence_based"

    @pytest.mark.asyncio
    async def test_resolve_voting(
        self, agent_a_id: UUID, agent_b_id: UUID, agent_c_id: UUID,
    ) -> None:
        resolver = ConflictResolver(strategy=ConflictResolutionStrategy.VOTING)
        outputs = {
            agent_a_id: {"recommendation": "open gate A"},
            agent_b_id: {"recommendation": "open gate A"},
            agent_c_id: {"recommendation": "close gate A"},
        }
        agents = [
            _make_agent(agent_a_id, "Agent A"),
            _make_agent(agent_b_id, "Agent B"),
            _make_agent(agent_c_id, "Agent C"),
        ]
        result = await resolver.resolve(outputs, agents)
        assert isinstance(result, Success)
        assert result.value["recommendation"] == "open gate A"
        assert result.value["_conflict_resolution"]["strategy"] == "voting"

    @pytest.mark.asyncio
    async def test_resolve_evidence_weighted(
        self, agent_a_id: UUID, agent_b_id: UUID,
    ) -> None:
        resolver = ConflictResolver(strategy=ConflictResolutionStrategy.EVIDENCE_WEIGHTED)
        outputs = {
            agent_a_id: {
                "recommendation": "rec A",
                "evidence": [
                    {"type": "sensor_data", "description": "real-time count"},
                    {"type": "real_time_sensor", "description": "live feed"},
                ],
            },
            agent_b_id: {
                "recommendation": "rec B",
                "evidence": [
                    {"type": "historical", "description": "last year data"},
                ],
            },
        }
        agents = [
            _make_agent(agent_a_id, "Agent A"),
            _make_agent(agent_b_id, "Agent B"),
        ]
        result = await resolver.resolve(outputs, agents)
        assert isinstance(result, Success)
        assert result.value["recommendation"] == "rec A"
        assert result.value["_conflict_resolution"]["strategy"] == "evidence_weighted"

    @pytest.mark.asyncio
    async def test_resolution_includes_participants(
        self, agent_a_id: UUID, agent_b_id: UUID,
    ) -> None:
        resolver = ConflictResolver()
        outputs = {
            agent_a_id: {"recommendation": "rec A", "confidence": 0.7},
            agent_b_id: {"recommendation": "rec B", "confidence": 0.8},
        }
        agents = [
            _make_agent(agent_a_id, "Agent Alpha"),
            _make_agent(agent_b_id, "Agent Beta"),
        ]
        result = await resolver.resolve(outputs, agents)
        assert isinstance(result, Success)
        resolution = result.value["_conflict_resolution"]
        assert resolution["conflicts_detected"] >= 1
        participant_names = [p["agent_name"] for p in resolution["participating_agents"]]
        assert "Agent Alpha" in participant_names
        assert "Agent Beta" in participant_names
