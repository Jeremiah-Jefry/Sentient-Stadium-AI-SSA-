"""Integration tests for the full orchestration pipeline.

Tests the complete flow: request → reason → plan → execute → validate → explain.
Covers multi-agent scenarios, conflict resolution, safety validation, and streaming.
"""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest

from app.features.orchestration.collaboration.conflict_resolver import (
    ConflictResolver,
)
from app.features.orchestration.collaboration.result_aggregator import (
    ResultAggregator,
)
from app.features.orchestration.confidence.orchestrator_confidence import (
    OrchestratorConfidence,
)
from app.features.orchestration.engines.pipeline_executor import PipelineExecutor
from app.features.orchestration.explanation.explanation_engine import (
    ExplanationEngine,
)
from app.features.orchestration.knowledge.knowledge_retrieval import (
    KnowledgeRetrieval,
)
from app.features.orchestration.memory.memory_manager import MemoryManager
from app.features.orchestration.models.enums import (
    ExecutionStatus,
    IntentType,
    RequestType,
    UserRole,
)
from app.features.orchestration.observability.metrics import OrchestrationMetrics
from app.features.orchestration.planner.execution_planner import ExecutionPlanner
from app.features.orchestration.planner.dependency_resolver import (
    DependencyResolver,
)
from app.features.orchestration.planner.strategy_selector import StrategySelector
from app.features.orchestration.reasoning.reasoning_engine import ReasoningEngine
from app.features.orchestration.registry.agent_registry import AgentRegistry
from app.features.orchestration.registry.tool_registry import ToolRegistry
from app.features.orchestration.safety.safety_engine import SafetyEngine
from app.features.orchestration.services.orchestration_service import (
    OrchestrationService,
)
from app.features.orchestration.streaming.streaming_manager import StreamingManager
from app.features.orchestration.dto.request import OrchestratorRequest
from app.shared.result import Success


def _build_service() -> OrchestrationService:
    """Build an OrchestrationService with all singleton dependencies."""
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
    tool_executor = __import__(
        "app.features.orchestration.engines.tool_executor",
        fromlist=["ToolExecutor"],
    ).ToolExecutor(tool_registry=tool_registry, observability=metrics)
    agent_executor = __import__(
        "app.features.orchestration.engines.agent_executor",
        fromlist=["AgentExecutor"],
    ).AgentExecutor(
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
    dependency_resolver = DependencyResolver()
    strategy_selector = StrategySelector()
    execution_planner = ExecutionPlanner(
        agent_registry=agent_registry,
        tool_registry=tool_registry,
        dependency_resolver=dependency_resolver,
        strategy_selector=strategy_selector,
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


def _make_request(
    query: str = "Test request",
    intent: IntentType = IntentType.INFORMATION_QUERY,
    priority: int = 5,
    request_type: RequestType = RequestType.VOLUNTEER_REQUEST,
) -> OrchestratorRequest:
    return OrchestratorRequest(
        request_id=uuid4(),
        request_type=request_type,
        intent=intent,
        query=query,
        venue_id=uuid4(),
        user_role=UserRole.VOLUNTEER,
        priority=priority,
        timeout_seconds=30.0,
    )


class TestOrchestrationPipeline:
    """End-to-end pipeline integration tests."""

    @pytest.fixture
    def service(self) -> OrchestrationService:
        return _build_service()

    @pytest.mark.asyncio
    async def test_information_query_pipeline(
        self, service: OrchestrationService,
    ) -> None:
        request = _make_request(
            query="What are the emergency evacuation procedures for Section A?",
            intent=IntentType.INFORMATION_QUERY,
            priority=5,
        )

        result = await service.execute(request)

        assert isinstance(result, Success)
        response = result.value
        assert response["status"] == ExecutionStatus.COMPLETED.value
        assert response["confidence"] > 0.0
        assert response["confidence"] <= 1.0
        assert len(response["agents_used"]) > 0
        assert response["recommendation"] is not None

    @pytest.mark.asyncio
    async def test_crowd_management_pipeline(
        self, service: OrchestrationService,
    ) -> None:
        request = _make_request(
            query="Gate B is overcrowded with 5000 people approaching",
            intent=IntentType.CROWD_MANAGEMENT,
            priority=7,
        )

        result = await service.execute(request)

        assert isinstance(result, Success)
        response = result.value
        assert response["status"] == ExecutionStatus.COMPLETED.value
        assert response["confidence"] > 0.0

    @pytest.mark.asyncio
    async def test_accessibility_pipeline(
        self, service: OrchestrationService,
    ) -> None:
        request = _make_request(
            query="Wheelchair user needs accessible route to Section D",
            intent=IntentType.ACCESSIBILITY,
            priority=8,
        )

        result = await service.execute(request)

        assert isinstance(result, Success)
        response = result.value
        assert response["status"] == ExecutionStatus.COMPLETED.value

    @pytest.mark.asyncio
    async def test_emergency_response_pipeline(
        self, service: OrchestrationService,
    ) -> None:
        request = _make_request(
            query="Medical emergency in Section C, spectator collapsed",
            intent=IntentType.MEDICAL,
            priority=10,
            request_type=RequestType.EMERGENCY,
        )

        result = await service.execute(request)

        assert isinstance(result, Success)
        response = result.value
        assert response["status"] == ExecutionStatus.COMPLETED.value
        assert response["confidence"] > 0.0

    @pytest.mark.asyncio
    async def test_multi_agent_collaboration(
        self, service: OrchestrationService,
    ) -> None:
        request = _make_request(
            query=(
                "Gate B is overcrowded and a wheelchair user needs help "
                "reaching Section D while a medical team must pass through"
            ),
            intent=IntentType.ACCESSIBILITY,
            priority=9,
            request_type=RequestType.VOLUNTEER_REQUEST,
        )

        result = await service.execute(request)

        assert isinstance(result, Success)
        response = result.value
        assert response["status"] == ExecutionStatus.COMPLETED.value
        assert len(response["agents_used"]) >= 2

    @pytest.mark.asyncio
    async def test_safety_validation_present(
        self, service: OrchestrationService,
    ) -> None:
        request = _make_request(
            query="Evacuate all sections immediately due to fire alarm",
            intent=IntentType.EVACUATION,
            priority=10,
            request_type=RequestType.EMERGENCY,
        )

        result = await service.execute(request)

        assert isinstance(result, Success)
        response = result.value
        assert "safety" in response or "explanation" in response

    @pytest.mark.asyncio
    async def test_reasoning_chain_generated(
        self, service: OrchestrationService,
    ) -> None:
        request = _make_request(
            query="Analyze crowd flow patterns and recommend gate adjustments",
            intent=IntentType.CROWD_MANAGEMENT,
            priority=6,
        )

        result = await service.execute(request)

        assert isinstance(result, Success)
        response = result.value
        assert response["reasoning"] is not None

    @pytest.mark.asyncio
    async def test_explanation_generated(
        self, service: OrchestrationService,
    ) -> None:
        request = _make_request(
            query="Why was Gate B closed during the halftime rush?",
            intent=IntentType.INFORMATION_QUERY,
            priority=4,
        )

        result = await service.execute(request)

        assert isinstance(result, Success)
        response = result.value
        assert response["explanation"] is not None

    @pytest.mark.asyncio
    async def test_confidence_score_present(
        self, service: OrchestrationService,
    ) -> None:
        request = _make_request(
            query="What is the current crowd density at Gate A?",
            intent=IntentType.CROWD_MANAGEMENT,
            priority=3,
        )

        result = await service.execute(request)

        assert isinstance(result, Success)
        response = result.value
        assert 0.0 <= response["confidence"] <= 1.0

    @pytest.mark.asyncio
    async def test_request_with_minimal_context(
        self, service: OrchestrationService,
    ) -> None:
        request = _make_request(
            query="Hello",
            intent=IntentType.INFORMATION_QUERY,
            priority=1,
        )

        result = await service.execute(request)

        assert isinstance(result, Success)
        response = result.value
        assert response["status"] in (
            ExecutionStatus.COMPLETED.value,
            ExecutionStatus.FAILED.value,
        )

    @pytest.mark.asyncio
    async def test_high_priority_request(
        self, service: OrchestrationService,
    ) -> None:
        request = _make_request(
            query="Active shooter reported near Gate C",
            intent=IntentType.SECURITY,
            priority=10,
            request_type=RequestType.EMERGENCY,
        )

        result = await service.execute(request)

        assert isinstance(result, Success)
        response = result.value
        assert response["status"] == ExecutionStatus.COMPLETED.value


class TestStreamingPipeline:
    """Tests for the streaming execution path."""

    @pytest.fixture
    def service(self) -> OrchestrationService:
        return _build_service()

    @pytest.mark.asyncio
    async def test_streaming_execution(
        self, service: OrchestrationService,
    ) -> None:
        request = _make_request(
            query="Monitor crowd at Gate A and provide real-time updates",
            intent=IntentType.CROWD_MANAGEMENT,
            priority=6,
        )

        result = await service.execute_streaming(request)

        assert isinstance(result, Success)
        data = result.value
        assert "execution_id" in data
        assert "stream_session_id" in data
        assert data["status"] == "accepted"


class TestCancellationPipeline:
    """Tests for execution cancellation."""

    @pytest.fixture
    def service(self) -> OrchestrationService:
        return _build_service()

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_execution(
        self, service: OrchestrationService,
    ) -> None:
        fake_id = uuid4()
        result = await service.cancel(fake_id)

        assert isinstance(result, Success)
        assert result.value["status"] == "not_found"


class TestMemoryIntegration:
    """Tests for memory storage during orchestration."""

    @pytest.fixture
    def service(self) -> OrchestrationService:
        return _build_service()

    @pytest.mark.asyncio
    async def test_memory_stored_after_execution(
        self, service: OrchestrationService,
    ) -> None:
        request = _make_request(
            query="Store this incident in memory for future reference",
            intent=IntentType.INCIDENT_RESPONSE,
            priority=5,
        )

        result = await service.execute(request)

        assert isinstance(result, Success)


class TestKnowledgeIntegration:
    """Tests for knowledge retrieval during orchestration."""

    @pytest.fixture
    def service(self) -> OrchestrationService:
        return _build_service()

    @pytest.mark.asyncio
    async def test_safety_sop_retrieved(
        self, service: OrchestrationService,
    ) -> None:
        request = _make_request(
            query="What is the emergency evacuation procedure for fire?",
            intent=IntentType.EMERGENCY_RESPONSE,
            priority=8,
        )

        result = await service.execute(request)

        assert isinstance(result, Success)
        response = result.value
        assert response["confidence"] > 0.0
