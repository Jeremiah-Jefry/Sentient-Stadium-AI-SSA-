from __future__ import annotations

import logging
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from uuid import UUID

logging = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class MetricsSummary:
    total_executions: int
    active_executions: int
    avg_duration_ms: float
    p50_duration_ms: float
    p95_duration_ms: float
    p99_duration_ms: float
    success_rate: float
    error_rate: float
    total_agent_invocations: int
    agent_invocations_by_type: dict[str, int]
    avg_confidence: float
    safety_violations_total: int
    conflicts_resolved: int
    cache_hit_rate: float


@dataclass
class _ExecutionRecord:
    request_type: str = ""
    status: str = "pending"
    duration_ms: float = 0.0
    steps: list[dict] = field(default_factory=list)
    tool_calls: list[dict] = field(default_factory=list)
    confidence_values: list[float] = field(default_factory=list)
    safety_violations: int = 0
    conflicts_resolved: int = 0
    reasoning_stages: list[dict] = field(default_factory=list)


class OrchestrationMetrics:
    def __init__(self) -> None:
        self._executions: dict[UUID, _ExecutionRecord] = {}
        self._completed_durations: list[float] = []
        self._completed_statuses: list[str] = []
        self._agent_invocations: dict[str, int] = defaultdict(int)
        self._total_agent_invocations: int = 0
        self._confidence_values: list[float] = []
        self._safety_violations_total: int = 0
        self._conflicts_resolved: int = 0
        self._tool_calls: list[dict] = []
        self._memory_operations: list[dict] = []
        self._knowledge_retrievals: list[dict] = []
        self._reasoning_stages: list[dict] = []

    def record_execution_start(self, execution_id: UUID, request_type: str) -> None:
        self._executions[execution_id] = _ExecutionRecord(request_type=request_type)
        logging.debug("Execution %s started (type=%s)", execution_id, request_type)

    def record_execution_complete(self, execution_id: UUID, status: str, duration_ms: float) -> None:
        record = self._executions.get(execution_id)
        if record is None:
            logging.warning("record_execution_complete for unknown execution %s", execution_id)
            return

        record.status = status
        record.duration_ms = duration_ms
        self._completed_durations.append(duration_ms)
        self._completed_statuses.append(status)

        logging.debug(
            "Execution %s completed (status=%s, duration=%.1fms)",
            execution_id, status, duration_ms,
        )

    def record_step_start(self, execution_id: UUID, step_id: UUID, agent_id: UUID, action: str) -> None:
        record = self._executions.get(execution_id)
        if record is None:
            return

        record.steps.append({
            "step_id": str(step_id),
            "agent_id": str(agent_id),
            "action": action,
            "status": "running",
        })

    def record_step_complete(self, execution_id: UUID, step_id: UUID, status: str, duration_ms: float) -> None:
        record = self._executions.get(execution_id)
        if record is None:
            return

        for step in record.steps:
            if step["step_id"] == str(step_id):
                step["status"] = status
                step["duration_ms"] = duration_ms
                break

    def record_tool_call(
        self, execution_id: UUID, tool_id: UUID, duration_ms: float, success: bool, cache_hit: bool,
    ) -> None:
        call_record = {
            "execution_id": str(execution_id),
            "tool_id": str(tool_id),
            "duration_ms": duration_ms,
            "success": success,
            "cache_hit": cache_hit,
        }
        self._tool_calls.append(call_record)

        record = self._executions.get(execution_id)
        if record is not None:
            record.tool_calls.append(call_record)

    def record_agent_error(self, agent_id: UUID, error_type: str) -> None:
        self._agent_invocations[f"error:{error_type}"] += 1
        logging.warning("Agent error recorded: agent=%s type=%s", agent_id, error_type)

    def record_conflict(self, execution_id: UUID, resolution_strategy: str) -> None:
        self._conflicts_resolved += 1

        record = self._executions.get(execution_id)
        if record is not None:
            record.conflicts_resolved += 1

        logging.debug("Conflict resolved in execution %s via %s", execution_id, resolution_strategy)

    def record_safety_check(self, execution_id: UUID, safety_level: str, violations: int) -> None:
        self._safety_violations_total += violations

        record = self._executions.get(execution_id)
        if record is not None:
            record.safety_violations += violations

        if violations > 0:
            logging.warning(
                "Safety violations in execution %s: level=%s count=%d",
                execution_id, safety_level, violations,
            )

    def record_confidence(self, execution_id: UUID, confidence: float) -> None:
        self._confidence_values.append(confidence)

        record = self._executions.get(execution_id)
        if record is not None:
            record.confidence_values.append(confidence)

    def record_memory_operation(self, operation: str, memory_type: str, duration_ms: float) -> None:
        self._memory_operations.append({
            "operation": operation,
            "memory_type": memory_type,
            "duration_ms": duration_ms,
        })

    def record_knowledge_retrieval(self, query: str, results_count: int, duration_ms: float) -> None:
        self._knowledge_retrievals.append({
            "query_length": len(query),
            "results_count": results_count,
            "duration_ms": duration_ms,
        })

    def record_reasoning_stage(self, execution_id: UUID, stage: str, duration_ms: float, confidence: float) -> None:
        stage_record = {
            "execution_id": str(execution_id),
            "stage": stage,
            "duration_ms": duration_ms,
            "confidence": confidence,
        }
        self._reasoning_stages.append(stage_record)

        record = self._executions.get(execution_id)
        if record is not None:
            record.reasoning_stages.append(stage_record)

    def get_metrics_summary(self) -> MetricsSummary:
        total = len(self._completed_durations)
        successes = sum(1 for s in self._completed_statuses if s == "completed")
        errors = total - successes
        active = sum(1 for r in self._executions.values() if r.status in ("pending", "executing"))

        avg_duration = statistics.mean(self._completed_durations) if self._completed_durations else 0.0
        p50 = self._percentile(self._completed_durations, 50.0)
        p95 = self._percentile(self._completed_durations, 95.0)
        p99 = self._percentile(self._completed_durations, 99.0)

        success_rate = successes / total if total > 0 else 0.0
        error_rate = errors / total if total > 0 else 0.0

        avg_confidence = statistics.mean(self._confidence_values) if self._confidence_values else 0.0

        total_tool_calls = len(self._tool_calls)
        cache_hits = sum(1 for tc in self._tool_calls if tc["cache_hit"])
        cache_hit_rate = cache_hits / total_tool_calls if total_tool_calls > 0 else 0.0

        return MetricsSummary(
            total_executions=total,
            active_executions=active,
            avg_duration_ms=round(avg_duration, 2),
            p50_duration_ms=round(p50, 2),
            p95_duration_ms=round(p95, 2),
            p99_duration_ms=round(p99, 2),
            success_rate=round(success_rate, 4),
            error_rate=round(error_rate, 4),
            total_agent_invocations=self._total_agent_invocations,
            agent_invocations_by_type=dict(self._agent_invocations),
            avg_confidence=round(avg_confidence, 4),
            safety_violations_total=self._safety_violations_total,
            conflicts_resolved=self._conflicts_resolved,
            cache_hit_rate=round(cache_hit_rate, 4),
        )

    def get_execution_graph(self, execution_id: UUID) -> dict:
        record = self._executions.get(execution_id)
        if record is None:
            return {"error": f"Execution {execution_id} not found"}

        steps = []
        for step in record.steps:
            steps.append({
                "step_id": step["step_id"],
                "agent_id": step["agent_id"],
                "action": step["action"],
                "status": step["status"],
                "duration_ms": step.get("duration_ms"),
            })

        tool_calls = [
            {
                "tool_id": tc["tool_id"],
                "duration_ms": tc["duration_ms"],
                "success": tc["success"],
                "cache_hit": tc["cache_hit"],
            }
            for tc in record.tool_calls
        ]

        return {
            "execution_id": str(execution_id),
            "request_type": record.request_type,
            "status": record.status,
            "duration_ms": record.duration_ms,
            "steps": steps,
            "tool_calls": tool_calls,
            "confidence_values": record.confidence_values,
            "safety_violations": record.safety_violations,
            "conflicts_resolved": record.conflicts_resolved,
            "reasoning_stages": record.reasoning_stages,
        }

    def reset(self) -> None:
        self._executions.clear()
        self._completed_durations.clear()
        self._completed_statuses.clear()
        self._agent_invocations.clear()
        self._total_agent_invocations = 0
        self._confidence_values.clear()
        self._safety_violations_total = 0
        self._conflicts_resolved = 0
        self._tool_calls.clear()
        self._memory_operations.clear()
        self._knowledge_retrievals.clear()
        self._reasoning_stages.clear()
        logging.info("All orchestration metrics reset")

    @staticmethod
    def _percentile(values: list[float], percentile: float) -> float:
        if not values:
            return 0.0
        sorted_values = sorted(values)
        index = (percentile / 100.0) * (len(sorted_values) - 1)
        lower = int(index)
        upper = lower + 1
        if upper >= len(sorted_values):
            return sorted_values[-1]
        fraction = index - lower
        return sorted_values[lower] + fraction * (sorted_values[upper] - sorted_values[lower])
