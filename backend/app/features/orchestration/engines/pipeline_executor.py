from __future__ import annotations

import asyncio
import logging
import time
from typing import Any
from uuid import UUID

from app.features.orchestration.dto.execution import ExecutionPlan, ExecutionStep
from app.features.orchestration.engines.agent_executor import AgentExecutor, AgentRegistry
from app.features.orchestration.engines.tool_executor import ToolExecutor
from app.features.orchestration.models.enums import StepStatus
from app.shared.result import Failure, Result, Success

logging = logging.getLogger(__name__)


class DependencyResolver:
    @staticmethod
    def resolve_waves(plan: ExecutionPlan) -> list[list[ExecutionStep]]:
        completed: set[UUID] = set()
        remaining = dict(plan.dependencies)
        waves: list[list[ExecutionStep]] = []

        while len(completed) < len(plan.steps):
            wave: list[ExecutionStep] = []
            for step in plan.steps:
                if step.step_id in completed:
                    continue
                deps = remaining.get(step.step_id, [])
                if all(d in completed for d in deps):
                    wave.append(step)

            if not wave:
                logging.error("Circular dependency detected; breaking deadlock")
                wave = [s for s in plan.steps if s.step_id not in completed][:1]

            for s in wave:
                completed.add(s.step_id)
            waves.append(wave)

        return waves


class PipelineExecutor:
    def __init__(
        self,
        agent_executor: AgentExecutor,
        tool_executor: ToolExecutor,
        agent_registry: AgentRegistry,
        observability: Any | None = None,
    ) -> None:
        self._agent_executor = agent_executor
        self._tool_executor = tool_executor
        self._agent_registry = agent_registry
        self._observability = observability

    async def execute_plan(
        self,
        plan: ExecutionPlan,
        context: dict,
        execution_id: UUID,
    ) -> Result[dict]:
        waves = DependencyResolver.resolve_waves(plan)
        all_step_results: dict[UUID, Result[dict]] = {}
        wave_timings: list[float] = []

        for _, wave in enumerate(waves):
            wave_start = time.monotonic()

            wave_results = await self._execute_wave(wave, context, execution_id)
            all_step_results.update(wave_results)

            wave_duration = (time.monotonic() - wave_start) * 1000
            wave_timings.append(wave_duration)

            for step in wave:
                if step.step_id in wave_results:
                    result = wave_results[step.step_id]
                    if isinstance(result, Failure):
                        retry_result = await self._execute_step_with_retry(
                            step, context, execution_id,
                        )
                        all_step_results[step.step_id] = retry_result

            failed_steps = [
                s for s in wave
                if isinstance(all_step_results.get(s.step_id), Failure)
            ]
            if failed_steps:
                for failed_step in failed_steps:
                    error_result = all_step_results[failed_step.step_id]
                    if isinstance(error_result, Failure):
                        degraded = await self._handle_step_failure(
                            failed_step, error_result.message, execution_id,
                        )
                        all_step_results[failed_step.step_id] = degraded

        aggregated = self._aggregate_results(all_step_results, plan)
        aggregated["execution_id"] = str(execution_id)
        aggregated["plan_id"] = str(plan.plan_id)
        aggregated["total_duration_ms"] = sum(wave_timings)
        aggregated["waves_executed"] = len(waves)
        aggregated["wave_timings_ms"] = wave_timings

        if self._observability is not None:
            self._observability.record_pipeline_execution(
                execution_id=execution_id,
                plan_id=plan.plan_id,
                total_duration_ms=sum(wave_timings),
                waves_executed=len(waves),
                step_results={
                    str(k): "success" if isinstance(v, Success) else "failure"
                    for k, v in all_step_results.items()
                },
            )

        return Success(value=aggregated)

    async def _execute_wave(
        self,
        wave: list[ExecutionStep],
        context: dict,
        execution_id: UUID,
    ) -> dict[UUID, Result[dict]]:
        tasks = [self._execute_step_with_retry(step, context, execution_id) for step in wave]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        wave_output: dict[UUID, Result[dict]] = {}
        for step, result in zip(wave, results, strict=False):
            if isinstance(result, Exception):
                wave_output[step.step_id] = Failure(
                    error_code="STEP_EXCEPTION",
                    message=f"Step {step.step_id} raised exception: {result}",
                )
            else:
                wave_output[step.step_id] = result

        return wave_output

    async def _execute_step_with_retry(
        self,
        step: ExecutionStep,
        context: dict,
        execution_id: UUID,
    ) -> Result[dict]:
        max_retries = step.retry_policy.max_retries
        backoff = step.retry_policy.backoff_seconds
        multiplier = step.retry_policy.backoff_multiplier
        current_delay = backoff

        for attempt in range(max_retries + 1):
            step_start = time.monotonic()

            result = await self._agent_executor.execute(step, context)
            latency_ms = (time.monotonic() - step_start) * 1000

            if isinstance(result, Success):
                result.value["_step_metadata"] = {
                    "step_id": str(step.step_id),
                    "agent_id": str(step.agent_id),
                    "action": step.action,
                    "attempt": attempt + 1,
                    "latency_ms": latency_ms,
                    "status": StepStatus.COMPLETED,
                }
                return result

            logging.warning(
                "Step %s attempt %d/%d failed: %s",
                step.step_id,
                attempt + 1,
                max_retries + 1,
                result.message,
            )

            if attempt < max_retries:
                await asyncio.sleep(current_delay)
                current_delay *= multiplier

        return Failure(
            error_code="STEP_MAX_RETRIES_EXCEEDED",
            message=f"Step {step.step_id} failed after {max_retries + 1} attempts",
            details={"step_id": str(step.step_id), "attempts": max_retries + 1},
        )

    async def _handle_step_failure(
        self,
        step: ExecutionStep,
        error: str,
        execution_id: UUID,
    ) -> Result[dict]:
        logging.warning(
            "Handling failure for step %s (agent=%s): %s",
            step.step_id,
            step.agent_name,
            error,
        )

        agent = self._agent_registry.get_agent(step.agent_id)
        degraded_output = {
            "_step_metadata": {
                "step_id": str(step.step_id),
                "agent_id": str(step.agent_id),
                "action": step.action,
                "status": StepStatus.FAILED,
            },
            "_degradation": {
                "original_error": error,
                "strategy": "graceful_fallback",
                "degraded_output": True,
                "agent_name": agent.metadata.name if agent else "unknown",
                "fallback_confidence": 0.3,
            },
            "confidence": 0.3,
            "evidence": [],
            "recommendations": ["Manual review recommended due to degraded agent output"],
        }

        return Success(value=degraded_output)

    def _aggregate_results(
        self,
        step_results: dict[UUID, Result[dict]],
        plan: ExecutionPlan,
    ) -> dict:
        successful: dict[UUID, dict] = {}
        failed: dict[UUID, str] = {}
        degraded: dict[UUID, bool] = {}

        for step_id, result in step_results.items():
            if isinstance(result, Success):
                output = result.value
                successful[step_id] = output
                if "_degradation" in output:
                    degraded[step_id] = True
            else:
                failed[step_id] = result.message

        all_confidences = []
        for output in successful.values():
            conf = output.get("confidence")
            if conf is not None:
                all_confidences.append(conf)

        overall_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0

        primary_recommendation = ""
        for output in successful.values():
            recs = output.get("recommendations") or output.get("route_options")
            if recs:
                if isinstance(recs, list) and recs:
                    primary_recommendation = (
                        str(recs[0]) if isinstance(recs[0], str)
                        else str(recs[0])
                    )
                break
        if not primary_recommendation and successful:
            first_output = next(iter(successful.values()))
            primary_recommendation = str(
                first_output.get(
                    "result",
                    first_output.get("status", "completed"),
                ),
            )

        all_evidence: list[dict] = []
        for output in successful.values():
            evidence = output.get("evidence", [])
            if isinstance(evidence, list):
                all_evidence.extend(evidence)

        agents_used = []
        for step in plan.steps:
            if step.step_id in successful or step.step_id in degraded:
                agents_used.append({
                    "agent_id": str(step.agent_id),
                    "agent_name": step.agent_name,
                    "action": step.action,
                    "degraded": step.step_id in degraded,
                })

        return {
            "recommendation": primary_recommendation,
            "confidence": overall_confidence,
            "steps_completed": len(successful),
            "steps_failed": len(failed),
            "steps_degraded": len(degraded),
            "total_steps": len(plan.steps),
            "evidence": all_evidence,
            "agents_used": agents_used,
            "step_outputs": {str(k): v for k, v in successful.items()},
            "failures": {str(k): v for k, v in failed.items()},
        }
