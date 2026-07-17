"""Dependency injection for Orchestration Engine module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.orchestration.collaboration.conflict_resolver import (
    ConflictResolver,
)
from app.features.orchestration.collaboration.result_aggregator import (
    ResultAggregator,
)
from app.features.orchestration.confidence.orchestrator_confidence import (
    OrchestratorConfidence,
)
from app.features.orchestration.engines.agent_executor import (
    AgentExecutor as _AgentExecutor,
)
from app.features.orchestration.engines.pipeline_executor import PipelineExecutor
from app.features.orchestration.engines.tool_executor import ToolExecutor
from app.features.orchestration.explanation.explanation_engine import (
    ExplanationEngine,
)
from app.features.orchestration.knowledge.knowledge_retrieval import (
    KnowledgeRetrieval,
)
from app.features.orchestration.memory.memory_manager import MemoryManager
from app.features.orchestration.observability.metrics import OrchestrationMetrics
from app.features.orchestration.planner.dependency_resolver import DependencyResolver
from app.features.orchestration.planner.execution_planner import ExecutionPlanner
from app.features.orchestration.planner.strategy_selector import StrategySelector
from app.features.orchestration.reasoning.reasoning_engine import ReasoningEngine
from app.features.orchestration.registry.agent_registry import AgentRegistry
from app.features.orchestration.registry.tool_registry import ToolRegistry
from app.features.orchestration.repositories.audit_repository import AuditRepository
from app.features.orchestration.repositories.decision_ledger_repository import (
    DecisionLedgerRepository,
)
from app.features.orchestration.repositories.execution_repository import (
    ExecutionRepository,
)
from app.features.orchestration.safety.safety_engine import SafetyEngine
from app.features.orchestration.streaming.streaming_manager import StreamingManager
from app.shared.database import get_db_session

if TYPE_CHECKING:
    from app.features.orchestration.services.orchestration_service import (
        OrchestrationService,
    )

# ---------------------------------------------------------------------------
# Module-level singletons
# ---------------------------------------------------------------------------
_agent_registry = AgentRegistry()
_tool_registry = ToolRegistry()
_memory_manager = MemoryManager()
_knowledge_retrieval = KnowledgeRetrieval()
_metrics = OrchestrationMetrics()
_streaming_manager = StreamingManager()
_safety_engine = SafetyEngine()
_orchestrator_confidence = OrchestratorConfidence()
_explanation_engine = ExplanationEngine()
_conflict_resolver = ConflictResolver()
_result_aggregator = ResultAggregator()

# Engines that need dependencies
_tool_executor = ToolExecutor(
    tool_registry=_tool_registry,
    observability=_metrics,
)

_agent_executor = _AgentExecutor(
    agent_registry=_agent_registry,  # type: ignore[arg-type]
    tool_executor=_tool_executor,
    observability=_metrics,
)

_pipeline_executor = PipelineExecutor(
    agent_executor=_agent_executor,
    tool_executor=_tool_executor,
    agent_registry=_agent_registry,  # type: ignore[arg-type]
    observability=_metrics,
)

_reasoning_engine = ReasoningEngine(
    knowledge_retrieval=_knowledge_retrieval,
    memory_manager=_memory_manager,
)

_dependency_resolver = DependencyResolver()
_strategy_selector = StrategySelector()
_execution_planner = ExecutionPlanner(
    agent_registry=_agent_registry,
    tool_registry=_tool_registry,
    dependency_resolver=_dependency_resolver,
    strategy_selector=_strategy_selector,
)


# ---------------------------------------------------------------------------
# Singleton getters (no DB required)
# ---------------------------------------------------------------------------

def get_agent_registry() -> AgentRegistry:
    return _agent_registry


def get_tool_registry() -> ToolRegistry:
    return _tool_registry


def get_streaming_manager() -> StreamingManager:
    return _streaming_manager


def get_metrics() -> OrchestrationMetrics:
    return _metrics


def get_memory_manager() -> MemoryManager:
    return _memory_manager


def get_knowledge_retrieval() -> KnowledgeRetrieval:
    return _knowledge_retrieval


def get_reasoning_engine() -> ReasoningEngine:
    return _reasoning_engine


def get_safety_engine() -> SafetyEngine:
    return _safety_engine


def get_orchestrator_confidence() -> OrchestratorConfidence:
    return _orchestrator_confidence


def get_explanation_engine() -> ExplanationEngine:
    return _explanation_engine


def get_conflict_resolver() -> ConflictResolver:
    return _conflict_resolver


def get_result_aggregator() -> ResultAggregator:
    return _result_aggregator


def get_pipeline_executor() -> PipelineExecutor:
    return _pipeline_executor


def get_execution_planner() -> ExecutionPlanner:
    return _execution_planner


# ---------------------------------------------------------------------------
# Per-request repositories (require database session)
# ---------------------------------------------------------------------------

async def get_execution_repo(
    session: AsyncSession = Depends(get_db_session),
) -> ExecutionRepository:
    return ExecutionRepository(session)


async def get_decision_ledger_repo(
    session: AsyncSession = Depends(get_db_session),
) -> DecisionLedgerRepository:
    return DecisionLedgerRepository(session)


async def get_audit_repo(
    session: AsyncSession = Depends(get_db_session),
) -> AuditRepository:
    return AuditRepository(session)


# ---------------------------------------------------------------------------
# Service factory
# ---------------------------------------------------------------------------

def _build_service(
    execution_repo: ExecutionRepository,
    decision_repo: DecisionLedgerRepository,
    audit_repo: AuditRepository,
) -> OrchestrationService:
    from app.features.orchestration.services.orchestration_service import (
        OrchestrationService,
    )

    return OrchestrationService(
        agent_registry=_agent_registry,
        tool_registry=_tool_registry,
        execution_planner=_execution_planner,
        pipeline_executor=_pipeline_executor,
        reasoning_engine=_reasoning_engine,
        safety_engine=_safety_engine,
        orchestrator_confidence=_orchestrator_confidence,
        explanation_engine=_explanation_engine,
        result_aggregator=_result_aggregator,
        conflict_resolver=_conflict_resolver,
        memory_manager=_memory_manager,
        knowledge_retrieval=_knowledge_retrieval,
        streaming_manager=_streaming_manager,
        metrics=_metrics,
        execution_repo=execution_repo,
        decision_repo=decision_repo,
        audit_repo=audit_repo,
    )


async def get_orchestration_service(
    execution_repo: ExecutionRepository = Depends(get_execution_repo),
    decision_repo: DecisionLedgerRepository = Depends(get_decision_ledger_repo),
    audit_repo: AuditRepository = Depends(get_audit_repo),
) -> OrchestrationService:
    return _build_service(execution_repo, decision_repo, audit_repo)
