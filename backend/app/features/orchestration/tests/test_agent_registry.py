"""Tests for AgentRegistry — dynamic registration, discovery, load tracking, and health management."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from app.features.orchestration.dto.agent import AgentCapability, AgentMetadata
from app.features.orchestration.dto.request import AgentSelectorCriteria
from app.features.orchestration.models.enums import AgentStatus
from app.features.orchestration.registry.agent_registry import AgentRegistry
from app.shared.result import Failure, Success


def _make_metadata(
    agent_id: UUID | None = None,
    name: str = "Test Agent",
    capabilities: list[str] | None = None,
    cost: float = 0.05,
    latency: float = 100.0,
    priority: int = 5,
    max_concurrent: int = 10,
) -> AgentMetadata:
    caps = [
        AgentCapability(name=c, description=f"Can do {c}")
        for c in (capabilities or ["test_action"])
    ]
    return AgentMetadata(
        agent_id=agent_id or uuid4(),
        name=name,
        description="Test agent",
        capabilities=caps,
        supported_actions=capabilities or ["test_action"],
        cost_per_invocation=cost,
        avg_latency_ms=latency,
        priority=priority,
        version="1.0.0",
        permissions=["read:test"],
        supported_tools=[],
        max_concurrent=max_concurrent,
    )


@pytest.fixture
def registry() -> AgentRegistry:
    return AgentRegistry()


class TestAgentRegistry:

    @pytest.mark.asyncio
    async def test_default_agents_registered(self, registry: AgentRegistry) -> None:
        agents = await registry.get_all_agents()
        assert len(agents) == 10
        names = {a.metadata.name for a in agents}
        assert "Crowd Intelligence Agent" in names
        assert "Navigation Agent" in names
        assert "Accessibility Agent" in names
        assert "Medical Agent" in names
        assert "Reasoning Agent" in names

    @pytest.mark.asyncio
    async def test_register_agent(self, registry: AgentRegistry) -> None:
        metadata = _make_metadata(name="Custom Agent")
        result = await registry.register_agent(metadata)
        assert isinstance(result, Success)
        agent = result.value
        assert agent.metadata.name == "Custom Agent"
        assert agent.status == AgentStatus.AVAILABLE
        assert agent.health_score == 1.0

    @pytest.mark.asyncio
    async def test_register_duplicate_agent(self, registry: AgentRegistry) -> None:
        metadata = _make_metadata(name="Duplicate Agent")
        result1 = await registry.register_agent(metadata)
        assert isinstance(result1, Success)
        result2 = await registry.register_agent(metadata)
        assert isinstance(result2, Failure)
        assert result2.error_code == "AGENT_ALREADY_REGISTERED"

    @pytest.mark.asyncio
    async def test_unregister_agent(self, registry: AgentRegistry) -> None:
        metadata = _make_metadata(name="Temporary Agent")
        await registry.register_agent(metadata)
        result = await registry.unregister_agent(metadata.agent_id)
        assert isinstance(result, Success)
        agent_result = await registry.get_agent(metadata.agent_id)
        assert isinstance(agent_result, Success)
        assert agent_result.value is None

    @pytest.mark.asyncio
    async def test_unregister_nonexistent_agent(self, registry: AgentRegistry) -> None:
        result = await registry.unregister_agent(uuid4())
        assert isinstance(result, Failure)
        assert result.error_code == "AGENT_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_get_agent(self, registry: AgentRegistry) -> None:
        metadata = _make_metadata(name="Fetchable Agent")
        await registry.register_agent(metadata)
        result = await registry.get_agent(metadata.agent_id)
        assert isinstance(result, Success)
        assert result.value is not None
        assert result.value.metadata.name == "Fetchable Agent"

    @pytest.mark.asyncio
    async def test_get_agent_not_found(self, registry: AgentRegistry) -> None:
        result = await registry.get_agent(uuid4())
        assert isinstance(result, Success)
        assert result.value is None

    @pytest.mark.asyncio
    async def test_find_agents_by_capabilities(self, registry: AgentRegistry) -> None:
        criteria = AgentSelectorCriteria(
            required_capabilities=["crowd_management"],
        )
        results = await registry.find_agents(criteria)
        assert len(results) >= 1
        assert all("crowd_management" in {c.name for c in a.metadata.capabilities} for a in results)

    @pytest.mark.asyncio
    async def test_find_agents_by_health(self, registry: AgentRegistry) -> None:
        metadata = _make_metadata(name="Sick Agent")
        await registry.register_agent(metadata)
        await registry.update_agent_health(metadata.agent_id, 0.3)

        criteria = AgentSelectorCriteria()
        results = await registry.find_agents(criteria)
        agent_ids = [a.metadata.agent_id for a in results]
        assert metadata.agent_id not in agent_ids

    @pytest.mark.asyncio
    async def test_find_agents_by_cost(self, registry: AgentRegistry) -> None:
        criteria = AgentSelectorCriteria(max_cost=0.01)
        results = await registry.find_agents(criteria)
        for agent in results:
            assert agent.metadata.cost_per_invocation <= 0.01

    @pytest.mark.asyncio
    async def test_find_agents_excludes_offline(self, registry: AgentRegistry) -> None:
        metadata = _make_metadata(name="Offline Agent")
        await registry.register_agent(metadata)
        await registry.update_agent_status(metadata.agent_id, AgentStatus.OFFLINE)

        criteria = AgentSelectorCriteria()
        results = await registry.find_agents(criteria)
        agent_ids = [a.metadata.agent_id for a in results]
        assert metadata.agent_id not in agent_ids

    @pytest.mark.asyncio
    async def test_update_agent_status(self, registry: AgentRegistry) -> None:
        metadata = _make_metadata(name="Status Agent")
        await registry.register_agent(metadata)
        result = await registry.update_agent_status(metadata.agent_id, AgentStatus.DEGRADED)
        assert isinstance(result, Success)
        agent_result = await registry.get_agent(metadata.agent_id)
        assert agent_result.value.status == AgentStatus.DEGRADED

    @pytest.mark.asyncio
    async def test_update_agent_status_not_found(self, registry: AgentRegistry) -> None:
        result = await registry.update_agent_status(uuid4(), AgentStatus.BUSY)
        assert isinstance(result, Failure)
        assert result.error_code == "AGENT_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_update_agent_health(self, registry: AgentRegistry) -> None:
        metadata = _make_metadata(name="Health Agent")
        await registry.register_agent(metadata)
        result = await registry.update_agent_health(metadata.agent_id, 0.75)
        assert isinstance(result, Success)
        agent_result = await registry.get_agent(metadata.agent_id)
        assert agent_result.value.health_score == 0.75

    @pytest.mark.asyncio
    async def test_update_agent_health_clamps(self, registry: AgentRegistry) -> None:
        metadata = _make_metadata(name="Clamp Agent")
        await registry.register_agent(metadata)
        await registry.update_agent_health(metadata.agent_id, 5.0)
        agent_result = await registry.get_agent(metadata.agent_id)
        assert agent_result.value.health_score == 1.0

        await registry.update_agent_health(metadata.agent_id, -1.0)
        agent_result = await registry.get_agent(metadata.agent_id)
        assert agent_result.value.health_score == 0.0

    @pytest.mark.asyncio
    async def test_record_invocation(self, registry: AgentRegistry) -> None:
        metadata = _make_metadata(name="Load Agent", max_concurrent=10)
        await registry.register_agent(metadata)
        await registry.record_invocation(metadata.agent_id)
        agent_result = await registry.get_agent(metadata.agent_id)
        assert agent_result.value.current_load == 1
        await registry.record_invocation(metadata.agent_id)
        agent_result = await registry.get_agent(metadata.agent_id)
        assert agent_result.value.current_load == 2

    @pytest.mark.asyncio
    async def test_record_completion(self, registry: AgentRegistry) -> None:
        metadata = _make_metadata(name="Complete Agent", max_concurrent=10)
        await registry.register_agent(metadata)
        await registry.record_invocation(metadata.agent_id)
        await registry.record_completion(metadata.agent_id, success=True, latency_ms=50.0)
        agent_result = await registry.get_agent(metadata.agent_id)
        assert agent_result.value.current_load == 0
        assert agent_result.value.status == AgentStatus.AVAILABLE

    @pytest.mark.asyncio
    async def test_record_completion_tracks_errors(self, registry: AgentRegistry) -> None:
        metadata = _make_metadata(name="Error Agent", max_concurrent=10)
        await registry.register_agent(metadata)
        await registry.record_invocation(metadata.agent_id)
        await registry.record_completion(metadata.agent_id, success=False, latency_ms=100.0)
        agent_result = await registry.get_agent(metadata.agent_id)
        assert agent_result.value.error_rate > 0.0

    @pytest.mark.asyncio
    async def test_get_healthy_agents(self, registry: AgentRegistry) -> None:
        healthy = await registry.get_healthy_agents()
        for agent in healthy:
            assert agent.health_score > 0.5
            assert agent.status in (AgentStatus.AVAILABLE, AgentStatus.BUSY)

    @pytest.mark.asyncio
    async def test_get_healthy_agents_excludes_unhealthy(self, registry: AgentRegistry) -> None:
        metadata = _make_metadata(name="Unhealthy Agent")
        await registry.register_agent(metadata)
        await registry.update_agent_health(metadata.agent_id, 0.2)
        healthy = await registry.get_healthy_agents()
        healthy_ids = [a.metadata.agent_id for a in healthy]
        assert metadata.agent_id not in healthy_ids

    @pytest.mark.asyncio
    async def test_stats(self, registry: AgentRegistry) -> None:
        stats = await registry.stats()
        assert stats["total_agents"] == 10
        assert "status_distribution" in stats
        assert stats["avg_health"] > 0.0
        assert stats["total_load"] >= 0

    @pytest.mark.asyncio
    async def test_status_change_callback(self, registry: AgentRegistry) -> None:
        changes: list[tuple[UUID, AgentStatus, AgentStatus]] = []
        registry.on_agent_status_change(lambda aid, old, new: changes.append((aid, old, new)))

        metadata = _make_metadata(name="Callback Agent")
        await registry.register_agent(metadata)
        await registry.update_agent_status(metadata.agent_id, AgentStatus.BUSY)
        assert len(changes) == 1
        assert changes[0][1] == AgentStatus.AVAILABLE
        assert changes[0][2] == AgentStatus.BUSY
