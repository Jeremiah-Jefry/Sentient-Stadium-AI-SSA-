"""Tests for OrchestrationConsumer — event-driven orchestration triggering."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from uuid import uuid4

import pytest

from app.features.orchestration.consumers.orchestration_consumer import (
    OrchestrationConsumer,
)
from app.features.orchestration.models.enums import IntentType
from app.features.orchestration.registry.agent_registry import AgentRegistry
from app.features.orchestration.registry.tool_registry import ToolRegistry
from app.features.orchestration.memory.memory_manager import MemoryManager
from app.features.orchestration.knowledge.knowledge_retrieval import (
    KnowledgeRetrieval,
)
from app.features.orchestration.observability.metrics import OrchestrationMetrics
from app.features.orchestration.safety.safety_engine import SafetyEngine
from app.features.orchestration.confidence.orchestrator_confidence import (
    OrchestratorConfidence,
)
from app.features.orchestration.explanation.explanation_engine import (
    ExplanationEngine,
)
from app.features.orchestration.collaboration.conflict_resolver import (
    ConflictResolver,
)
from app.features.orchestration.collaboration.result_aggregator import (
    ResultAggregator,
)
from app.features.orchestration.reasoning.reasoning_engine import ReasoningEngine
from app.features.orchestration.engines.pipeline_executor import PipelineExecutor
from app.features.orchestration.planner.execution_planner import ExecutionPlanner
from app.features.orchestration.planner.dependency_resolver import (
    DependencyResolver,
)
from app.features.orchestration.planner.strategy_selector import StrategySelector
from app.features.orchestration.streaming.streaming_manager import StreamingManager
from app.features.orchestration.services.orchestration_service import (
    OrchestrationService,
)


@dataclass
class FakeEventBusEvent:
    """Minimal EventBusEvent for testing."""

    event_id: str = ""
    category: str = "crowd"
    event_type: str = "crowd_density_critical"
    payload: dict = None  # type: ignore[assignment]
    venue_id: str | None = None
    zone_id: str | None = None
    priority: str = "high"
    severity: str = "warning"
    captured_at: str = ""
    producer: str = "test"

    def __post_init__(self) -> None:
        if self.payload is None:
            self.payload = {"description": "Test event"}
        if not self.event_id:
            self.event_id = str(uuid4())


def _build_service() -> OrchestrationService:
    agent_registry = AgentRegistry()
    tool_registry = ToolRegistry()
    memory_manager = MemoryManager()
    knowledge_retrieval = KnowledgeRetrieval()
    metrics = OrchestrationMetrics()
    streaming_manager = StreamingManager()
    safety_engine = SafetyEngine()
    confidence_engine = OrchestratorConfidence()
    explanation_engine = ExplanationEngine()
    conflict_resolver = ConflictResolver()
    result_aggregator = ResultAggregator()
    reasoning_engine = ReasoningEngine(
        knowledge_retrieval=knowledge_retrieval,
        memory_manager=memory_manager,
    )
    from app.features.orchestration.engines.tool_executor import ToolExecutor
    from app.features.orchestration.engines.agent_executor import AgentExecutor

    tool_executor = ToolExecutor(
        tool_registry=tool_registry, observability=metrics,
    )
    agent_executor = AgentExecutor(
        agent_registry=agent_registry,
        tool_executor=tool_executor,
        observability=metrics,
    )
    pipeline_executor = PipelineExecutor(
        agent_executor=agent_executor,
        tool_executor=tool_executor,
        agent_registry=agent_registry,
        observability=metrics,
    )
    execution_planner = ExecutionPlanner(
        agent_registry=agent_registry,
        tool_registry=tool_registry,
        dependency_resolver=DependencyResolver(),
        strategy_selector=StrategySelector(),
    )

    return OrchestrationService(
        agent_registry=agent_registry,
        tool_registry=tool_registry,
        execution_planner=execution_planner,
        pipeline_executor=pipeline_executor,
        reasoning_engine=reasoning_engine,
        safety_engine=safety_engine,
        orchestrator_confidence=confidence_engine,
        explanation_engine=explanation_engine,
        result_aggregator=result_aggregator,
        conflict_resolver=conflict_resolver,
        memory_manager=memory_manager,
        knowledge_retrieval=knowledge_retrieval,
        streaming_manager=streaming_manager,
        metrics=metrics,
    )


class TestOrchestrationConsumer:
    """Tests for the event-driven orchestration consumer."""

    @pytest.fixture
    def consumer(self) -> OrchestrationConsumer:
        return OrchestrationConsumer(service=_build_service())

    @pytest.mark.asyncio
    async def test_consumer_starts_and_stops(
        self, consumer: OrchestrationConsumer,
    ) -> None:
        await consumer.start()
        assert consumer._running is True
        assert consumer.stats["running"] == 1

        await consumer.stop()
        assert consumer._running is False
        assert consumer.stats["running"] == 0

    @pytest.mark.asyncio
    async def test_crowd_event_triggers_orchestration(
        self, consumer: OrchestrationConsumer,
    ) -> None:
        await consumer.start()
        event = FakeEventBusEvent(
            event_type="crowd_density_critical",
            category="crowd",
            payload={"description": "Critical density at Gate B"},
        )

        await consumer.handle_event(event)

        assert consumer.stats["processed"] == 1
        assert consumer.stats["errors"] == 0
        await consumer.stop()

    @pytest.mark.asyncio
    async def test_emergency_event_high_priority(
        self, consumer: OrchestrationConsumer,
    ) -> None:
        await consumer.start()
        event = FakeEventBusEvent(
            event_type="emergency_detected",
            category="emergency",
            payload={"description": "Fire alarm in Section A"},
        )

        await consumer.handle_event(event)

        assert consumer.stats["processed"] == 1
        await consumer.stop()

    @pytest.mark.asyncio
    async def test_unknown_event_type_ignored(
        self, consumer: OrchestrationConsumer,
    ) -> None:
        await consumer.start()
        event = FakeEventBusEvent(
            event_type="unknown_event_type",
            category="other",
        )

        await consumer.handle_event(event)

        assert consumer.stats["processed"] == 0
        assert consumer.stats["errors"] == 0
        await consumer.stop()

    @pytest.mark.asyncio
    async def test_consumer_ignores_when_stopped(
        self, consumer: OrchestrationConsumer,
    ) -> None:
        event = FakeEventBusEvent(event_type="crowd_density_critical")

        await consumer.handle_event(event)

        assert consumer.stats["processed"] == 0
        await consumer.stop()

    @pytest.mark.asyncio
    async def test_multiple_events_processed(
        self, consumer: OrchestrationConsumer,
    ) -> None:
        await consumer.start()

        events = [
            FakeEventBusEvent(event_type="crowd_density_critical"),
            FakeEventBusEvent(event_type="medical_emergency"),
            FakeEventBusEvent(event_type="security_alert"),
        ]

        for event in events:
            await consumer.handle_event(event)

        assert consumer.stats["processed"] == 3
        await consumer.stop()

    @pytest.mark.asyncio
    async def test_stats_property(self, consumer: OrchestrationConsumer) -> None:
        await consumer.start()
        stats = consumer.stats
        assert "processed" in stats
        assert "errors" in stats
        assert "running" in stats
        await consumer.stop()
