"""Tests for OrchestrationMetrics — execution tracking, aggregate summaries, percentiles, and reset."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.features.orchestration.observability.metrics import OrchestrationMetrics


@pytest.fixture
def metrics() -> OrchestrationMetrics:
    return OrchestrationMetrics()


class TestOrchestrationMetrics:

    def test_record_execution_lifecycle(self, metrics: OrchestrationMetrics) -> None:
        exec_id = uuid4()
        metrics.record_execution_start(exec_id, request_type="volunteer_request")
        summary = metrics.get_metrics_summary()
        assert summary.active_executions == 1

        metrics.record_execution_complete(exec_id, status="completed", duration_ms=150.0)
        summary = metrics.get_metrics_summary()
        assert summary.active_executions == 0
        assert summary.total_executions == 1
        assert summary.success_rate == 1.0

    def test_record_execution_failed(self, metrics: OrchestrationMetrics) -> None:
        exec_id = uuid4()
        metrics.record_execution_start(exec_id, request_type="admin_request")
        metrics.record_execution_complete(exec_id, status="failed", duration_ms=50.0)
        summary = metrics.get_metrics_summary()
        assert summary.total_executions == 1
        assert summary.error_rate == 1.0
        assert summary.success_rate == 0.0

    def test_metrics_summary(self, metrics: OrchestrationMetrics) -> None:
        for i in range(5):
            eid = uuid4()
            metrics.record_execution_start(eid, request_type="volunteer_request")
            metrics.record_execution_complete(eid, status="completed", duration_ms=100.0 + i * 50)

        summary = metrics.get_metrics_summary()
        assert summary.total_executions == 5
        assert summary.avg_duration_ms > 0
        assert summary.success_rate == 1.0
        assert summary.error_rate == 0.0

    def test_percentile_computation(self, metrics: OrchestrationMetrics) -> None:
        durations = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
        for d in durations:
            eid = uuid4()
            metrics.record_execution_start(eid, request_type="test")
            metrics.record_execution_complete(eid, status="completed", duration_ms=d)

        summary = metrics.get_metrics_summary()
        assert summary.p50_duration_ms > 0
        assert summary.p95_duration_ms >= summary.p50_duration_ms
        assert summary.p99_duration_ms >= summary.p95_duration_ms

    def test_percentile_single_value(self, metrics: OrchestrationMetrics) -> None:
        eid = uuid4()
        metrics.record_execution_start(eid, request_type="test")
        metrics.record_execution_complete(eid, status="completed", duration_ms=42.0)
        summary = metrics.get_metrics_summary()
        assert summary.p50_duration_ms == 42.0
        assert summary.p95_duration_ms == 42.0
        assert summary.p99_duration_ms == 42.0

    def test_percentile_empty(self, metrics: OrchestrationMetrics) -> None:
        summary = metrics.get_metrics_summary()
        assert summary.p50_duration_ms == 0.0
        assert summary.p95_duration_ms == 0.0
        assert summary.p99_duration_ms == 0.0

    def test_record_step(self, metrics: OrchestrationMetrics) -> None:
        exec_id = uuid4()
        step_id = uuid4()
        agent_id = uuid4()
        metrics.record_execution_start(exec_id, request_type="test")
        metrics.record_step_start(exec_id, step_id, agent_id, action="crowd_analysis")
        metrics.record_step_complete(exec_id, step_id, status="completed", duration_ms=25.0)

        graph = metrics.get_execution_graph(exec_id)
        assert len(graph["steps"]) == 1
        assert graph["steps"][0]["status"] == "completed"
        assert graph["steps"][0]["duration_ms"] == 25.0

    def test_record_tool_call(self, metrics: OrchestrationMetrics) -> None:
        exec_id = uuid4()
        tool_id = uuid4()
        metrics.record_execution_start(exec_id, request_type="test")
        metrics.record_tool_call(exec_id, tool_id, duration_ms=12.0, success=True, cache_hit=False)
        metrics.record_tool_call(exec_id, tool_id, duration_ms=0.0, success=True, cache_hit=True)

        summary = metrics.get_metrics_summary()
        assert summary.cache_hit_rate == 0.5

    def test_record_conflict(self, metrics: OrchestrationMetrics) -> None:
        exec_id = uuid4()
        metrics.record_execution_start(exec_id, request_type="test")
        metrics.record_conflict(exec_id, resolution_strategy="voting")
        metrics.record_conflict(exec_id, resolution_strategy="priority_based")

        summary = metrics.get_metrics_summary()
        assert summary.conflicts_resolved == 2

    def test_record_safety_check(self, metrics: OrchestrationMetrics) -> None:
        exec_id = uuid4()
        metrics.record_execution_start(exec_id, request_type="test")
        metrics.record_safety_check(exec_id, safety_level="warning", violations=2)

        summary = metrics.get_metrics_summary()
        assert summary.safety_violations_total == 2

    def test_record_confidence(self, metrics: OrchestrationMetrics) -> None:
        exec_id = uuid4()
        metrics.record_execution_start(exec_id, request_type="test")
        metrics.record_confidence(exec_id, 0.85)
        metrics.record_confidence(exec_id, 0.92)

        summary = metrics.get_metrics_summary()
        assert 0.85 <= summary.avg_confidence <= 0.92

    def test_record_reasoning_stage(self, metrics: OrchestrationMetrics) -> None:
        exec_id = uuid4()
        metrics.record_execution_start(exec_id, request_type="test")
        metrics.record_reasoning_stage(exec_id, "observe", duration_ms=10.0, confidence=0.8)

        graph = metrics.get_execution_graph(exec_id)
        assert len(graph["reasoning_stages"]) == 1
        assert graph["reasoning_stages"][0]["stage"] == "observe"

    def test_get_execution_graph_not_found(self, metrics: OrchestrationMetrics) -> None:
        graph = metrics.get_execution_graph(uuid4())
        assert "error" in graph

    def test_reset(self, metrics: OrchestrationMetrics) -> None:
        eid = uuid4()
        metrics.record_execution_start(eid, request_type="test")
        metrics.record_execution_complete(eid, status="completed", duration_ms=100.0)
        metrics.record_confidence(eid, 0.9)
        metrics.record_safety_check(eid, safety_level="safe", violations=0)

        metrics.reset()
        summary = metrics.get_metrics_summary()
        assert summary.total_executions == 0
        assert summary.avg_confidence == 0.0
        assert summary.safety_violations_total == 0
        assert summary.conflicts_resolved == 0

    def test_record_agent_error(self, metrics: OrchestrationMetrics) -> None:
        agent_id = uuid4()
        metrics.record_agent_error(agent_id, "timeout")
        metrics.record_agent_error(agent_id, "timeout")
        summary = metrics.get_metrics_summary()
        assert summary.agent_invocations_by_type.get("error:timeout", 0) == 2

    def test_record_memory_operation(self, metrics: OrchestrationMetrics) -> None:
        metrics.record_memory_operation("store", "conversation", 5.0)
        metrics.record_memory_operation("retrieve", "operational", 2.0)
        assert len(metrics._memory_operations) == 2

    def test_record_knowledge_retrieval(self, metrics: OrchestrationMetrics) -> None:
        metrics.record_knowledge_retrieval("crowd safety", 3, 15.0)
        assert len(metrics._knowledge_retrievals) == 1
        assert metrics._knowledge_retrievals[0]["results_count"] == 3
