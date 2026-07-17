"""Orchestration service — the brain of StadiumMind OS.

Coordinates the full pipeline: receive → understand → plan → execute → validate → explain → respond.
No module may directly call an LLM. Every AI interaction passes through this engine.
"""

from __future__ import annotations

import logging
import time
from uuid import UUID, uuid4

from app.features.orchestration.collaboration.conflict_resolver import ConflictResolver
from app.features.orchestration.collaboration.result_aggregator import ResultAggregator
from app.features.orchestration.confidence.orchestrator_confidence import OrchestratorConfidence
from app.features.orchestration.dto.request import OrchestratorRequest
from app.features.orchestration.engines.pipeline_executor import PipelineExecutor
from app.features.orchestration.explanation.explanation_engine import ExplanationEngine
from app.features.orchestration.knowledge.knowledge_retrieval import KnowledgeRetrieval
from app.features.orchestration.memory.memory_manager import MemoryManager
from app.features.orchestration.models.enums import ExecutionStatus, MemoryType
from app.features.orchestration.observability.metrics import OrchestrationMetrics
from app.features.orchestration.planner.execution_planner import ExecutionPlanner
from app.features.orchestration.reasoning.reasoning_engine import ReasoningEngine
from app.features.orchestration.registry.agent_registry import AgentRegistry
from app.features.orchestration.registry.tool_registry import ToolRegistry
from app.features.orchestration.repositories.audit_repository import AuditRepository
from app.features.orchestration.repositories.decision_ledger_repository import (
    DecisionLedgerRepository,
)
from app.features.orchestration.repositories.execution_repository import ExecutionRepository
from app.features.orchestration.safety.safety_engine import SafetyEngine
from app.features.orchestration.streaming.streaming_manager import StreamingManager
from app.shared.result import Failure, Result, Success

logger = logging.getLogger(__name__)


class OrchestrationService:
    """Main orchestration service — the single entry point for all AI requests."""

    def __init__(
        self,
        agent_registry: AgentRegistry,
        tool_registry: ToolRegistry,
        execution_planner: ExecutionPlanner,
        pipeline_executor: PipelineExecutor,
        reasoning_engine: ReasoningEngine,
        safety_engine: SafetyEngine,
        orchestrator_confidence: OrchestratorConfidence,
        explanation_engine: ExplanationEngine,
        result_aggregator: ResultAggregator,
        conflict_resolver: ConflictResolver,
        memory_manager: MemoryManager,
        knowledge_retrieval: KnowledgeRetrieval,
        streaming_manager: StreamingManager,
        metrics: OrchestrationMetrics,
        execution_repo: ExecutionRepository | None = None,
        decision_repo: DecisionLedgerRepository | None = None,
        audit_repo: AuditRepository | None = None,
    ) -> None:
        self._agent_registry = agent_registry
        self._tool_registry = tool_registry
        self._planner = execution_planner
        self._pipeline = pipeline_executor
        self._reasoning = reasoning_engine
        self._safety = safety_engine
        self._confidence = orchestrator_confidence
        self._explanation = explanation_engine
        self._aggregator = result_aggregator
        self._conflict_resolver = conflict_resolver
        self._memory = memory_manager
        self._knowledge = knowledge_retrieval
        self._streaming = streaming_manager
        self._metrics = metrics
        self._execution_repo = execution_repo
        self._decision_repo = decision_repo
        self._audit_repo = audit_repo

    async def execute(self, request: OrchestratorRequest) -> Result[dict]:
        execution_id = uuid4()
        start_ms = time.monotonic() * 1000
        self._metrics.record_execution_start(execution_id, request.request_type.value)

        try:
            result = await self._run_pipeline(request, execution_id)
        except Exception as exc:
            logger.exception("Orchestration failed for %s", request.request_id)
            self._metrics.record_execution_complete(execution_id, "failed", time.monotonic() * 1000 - start_ms)
            return Failure(error_code="ORCHESTRATION_FAILED", message=str(exc))

        duration_ms = time.monotonic() * 1000 - start_ms
        self._metrics.record_execution_complete(execution_id, "completed", duration_ms)
        await self._persist_results(execution_id, request, result)
        await self._store_memory(request, result)
        result["execution_id"] = str(execution_id)
        result["duration_ms"] = duration_ms
        return Success(result)

    async def _run_pipeline(self, request: OrchestratorRequest, execution_id: UUID) -> dict:
        reasoning_result = await self._reasoning.reason(request, request.context)
        reasoning_chain = reasoning_result.value if isinstance(reasoning_result, Success) else None

        context = await self._gather_context(request)
        plan_result = await self._planner.plan(request, context)
        if isinstance(plan_result, Failure):
            return self._build_fallback_response(request, execution_id, plan_result.message)
        plan = plan_result.value

        exec_result = await self._pipeline.execute_plan(plan, context, execution_id)
        if isinstance(exec_result, Failure):
            return self._build_fallback_response(request, execution_id, exec_result.message)
        raw_output = exec_result.value

        safety_result = await self._safety.validate(raw_output, context, request.user_role)
        safety_report = safety_result.value if isinstance(safety_result, Success) else None

        if safety_report and not safety_report.is_safe:
            logger.warning("Safety violation for %s: %s", request.request_id, safety_report.safety_level)
            if safety_report.safety_level.value in ("critical", "dangerous"):
                return self._build_safety_blocked_response(execution_id, request, safety_report)

        agent_outputs = raw_output.get("step_outputs", {})
        confidence_report = None
        if reasoning_chain and safety_report:
            conf_result = await self._confidence.compute(
                raw_output.get("step_outputs", {}),
                agent_outputs,
                reasoning_chain,
                safety_report,
            )
            confidence_report = conf_result if isinstance(conf_result, type(conf_result)) else conf_result

        explanation_result = None
        if reasoning_chain and confidence_report and safety_report:
            explanation_result = await self._explanation.explain(
                raw_output,
                self._to_explanation_chain(reasoning_chain),
                agent_outputs,
                self._to_explanation_confidence(confidence_report),
                self._to_explanation_safety(safety_report),
                request.user_role,
                context,
            )

        return self._build_response(
            request, execution_id, raw_output,
            reasoning_chain, safety_report, confidence_report, explanation_result,
        )

    async def _gather_context(self, request: OrchestratorRequest) -> dict:
        context = dict(request.context)
        if request.venue_id:
            mem_result = await self._memory.get_operational_context(request.venue_id)
            if isinstance(mem_result, Success):
                context["operational_memory"] = mem_result.value
        knowledge_result = await self._knowledge.retrieve(request.query, limit=5)
        if isinstance(knowledge_result, Success):
            context["knowledge_items"] = knowledge_result.value
        return context

    def _build_response(
        self, request: OrchestratorRequest, execution_id: UUID,
        raw: dict, reasoning_chain, safety_report, confidence_report, explanation_result,
    ) -> dict:
        confidence_val = confidence_report.overall if confidence_report else raw.get("confidence", 0.5)
        explanation_data = {}
        if isinstance(explanation_result, Success):
            exp = explanation_result.value
            explanation_data = {
                "decision_summary": exp.decision_summary,
                "reasoning_summary": exp.reasoning_summary,
                "expected_outcome": exp.expected_outcome,
                "limitations": exp.limitations,
                "depth_level": exp.depth_level,
            }
        return {
            "request_id": str(request.request_id),
            "execution_id": str(execution_id),
            "status": ExecutionStatus.COMPLETED.value,
            "recommendation": raw.get("recommendation", ""),
            "confidence": confidence_val,
            "reasoning": {"summary": reasoning_chain.summary if reasoning_chain else ""},
            "evidence": raw.get("evidence", []),
            "agents_used": raw.get("agents_used", []),
            "alternatives": [],
            "explanation": explanation_data,
            "safety_level": safety_report.safety_level.value if safety_report else "unknown",
            "metadata": {"strategy": raw.get("strategy", "unknown")},
        }

    def _build_fallback_response(self, request: OrchestratorRequest, execution_id: UUID, error: str) -> dict:
        return {
            "request_id": str(request.request_id),
            "execution_id": str(execution_id),
            "status": ExecutionStatus.FAILED.value,
            "recommendation": "Unable to generate recommendation. Manual review required.",
            "confidence": 0.0,
            "reasoning": {"error": error},
            "evidence": [],
            "agents_used": [],
            "alternatives": [],
            "explanation": {},
            "safety_level": "unknown",
            "metadata": {"error": error},
        }

    def _build_safety_blocked_response(self, execution_id: UUID, request: OrchestratorRequest, safety_report) -> dict:
        return {
            "request_id": str(request.request_id),
            "execution_id": str(execution_id),
            "status": ExecutionStatus.COMPLETED.value,
            "recommendation": "Recommendation blocked by safety engine. Human review required.",
            "confidence": 0.0,
            "reasoning": {"safety_block": True, "violations": len(safety_report.violations)},
            "evidence": [],
            "agents_used": [],
            "alternatives": [],
            "explanation": {},
            "safety_level": safety_report.safety_level.value,
            "metadata": {"safety_blocked": True},
        }

    @staticmethod
    def _to_explanation_chain(chain):
        from app.features.orchestration.explanation.types import ReasoningChain as ExplChain
        return ExplChain(
            stages=[{"name": s.stage.value, "confidence": s.confidence, "output": s.output} for s in chain.stages],
            final_reasoning=chain.summary,
            stage_count=len(chain.stages),
            duration_ms=chain.total_duration_ms,
        )

    @staticmethod
    def _to_explanation_confidence(report):
        from app.features.orchestration.explanation.types import ConfidenceReport as ExplConf
        return ExplConf(
            overall=report.overall,
            per_agent=report.per_agent,
            evidence_quality=report.evidence_strength,
            data_freshness=report.data_freshness,
            reasoning=report.reasoning_quality,
        )

    @staticmethod
    def _to_explanation_safety(report):
        from app.features.orchestration.explanation.types import SafetyReport as ExplSafety
        return ExplSafety(
            safety_level=report.safety_level.value,
            violations=report.violations,
            warnings=report.warnings,
            requires_human_review=report.safety_level.value in ("critical", "requires_human_review"),
        )

    async def _persist_results(self, execution_id: UUID, request: OrchestratorRequest, result: dict) -> None:
        if self._decision_repo:
            from app.features.orchestration.models.database import DecisionLedger
            entry = DecisionLedger(
                execution_id=execution_id,
                request_id=request.request_id,
                decision=result.get("recommendation", ""),
                reasoning=result.get("reasoning", {}).get("summary", ""),
                confidence=result.get("confidence", 0.0),
                agents_involved=[str(a.get("agent_id", "")) for a in result.get("agents_used", [])],
                evidence=result.get("evidence", []),
                alternatives=result.get("alternatives", []),
                safety_level=result.get("safety_level", "safe"),
            )
            await self._decision_repo.save(entry)
        if self._audit_repo:
            from app.features.orchestration.models.database import OrchestrationAuditLog
            log_entry = OrchestrationAuditLog(
                execution_id=execution_id,
                event_type="orchestration_completed",
                details={"request_type": request.request_type.value, "confidence": result.get("confidence", 0.0)},
            )
            await self._audit_repo.save(log_entry)

    async def _store_memory(self, request: OrchestratorRequest, result: dict) -> None:
        await self._memory.store(
            MemoryType.CONVERSATION, str(request.request_id),
            {"request": request.query, "response": result.get("recommendation", ""), "confidence": result.get("confidence", 0.0)},
        )

    async def execute_streaming(self, request: OrchestratorRequest) -> Result[dict]:
        execution_id = uuid4()
        session = await self._streaming.create_stream(execution_id)
        result = await self.execute(request)
        await self._streaming.complete_stream(session.session_id)
        if isinstance(result, Failure):
            return result
        return Success({"execution_id": execution_id, "stream_session_id": session.session_id})

    async def cancel(self, execution_id: UUID) -> Result[None]:
        active = self._streaming.get_active_sessions()
        for session in active:
            if session.execution_id == execution_id:
                await self._streaming.cancel_stream(session.session_id)
        return Success(None)

    async def get_agents_status(self) -> Result[list[dict]]:
        agents = await self._agent_registry.get_all_agents()
        return Success([
            {
                "agent_id": str(a.metadata.agent_id),
                "name": a.metadata.name,
                "status": a.status.value,
                "capabilities": [c.name for c in a.metadata.capabilities],
                "current_load": a.current_load,
                "health_score": a.health_score,
            }
            for a in agents
        ])

    async def get_metrics(self) -> dict:
        return self._metrics.get_metrics_summary().__dict__

    async def health_check(self) -> dict:
        agent_stats = await self._agent_registry.stats()
        return {
            "status": "healthy",
            "module": "orchestration",
            "agents": agent_stats,
            "tools": self._tool_registry.stats(),
            "metrics": self._metrics.get_metrics_summary().__dict__,
        }
