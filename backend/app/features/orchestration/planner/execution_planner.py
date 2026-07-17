"""AI-powered execution planner - generates execution plans from orchestrator requests."""

from __future__ import annotations

import logging
import uuid
from uuid import UUID

from app.features.orchestration.dto.agent import RegisteredAgent
from app.features.orchestration.dto.execution import (
    ExecutionPlan,
    ExecutionStep,
    RetryPolicy,
)
from app.features.orchestration.dto.request import (
    AgentSelectorCriteria,
    OrchestratorRequest,
)
from app.features.orchestration.exceptions import PlannerError
from app.features.orchestration.models.enums import IntentType
from app.features.orchestration.planner.dependency_resolver import (
    DependencyResolver,
)
from app.features.orchestration.planner.strategy_selector import (
    StrategySelector,
)
from app.features.orchestration.registry.agent_registry import AgentRegistry
from app.features.orchestration.registry.tool_registry import ToolRegistry
from app.shared.result import Failure, Result, Success

logger = logging.getLogger(__name__)

_INTENT_TO_CAPABILITIES: dict[IntentType, list[str]] = {
    IntentType.CROWD_MANAGEMENT: [
        "crowd_management", "density_analysis",
        "bottleneck_detection",
    ],
    IntentType.NAVIGATION: ["routing", "pathfinding", "rerouting"],
    IntentType.EMERGENCY_RESPONSE: [
        "incident_detection", "incident_response",
        "medical_response", "evacuation_transport",
    ],
    IntentType.ACCESSIBILITY: [
        "wheelchair_access", "accessibility_routing",
        "accessibility_assessment",
    ],
    IntentType.MEDICAL: [
        "medical_response", "first_aid", "triage",
        "emergency_medical",
    ],
    IntentType.RESOURCE_ALLOCATION: [
        "transit_management", "parking", "shuttle",
    ],
    IntentType.INFORMATION_QUERY: [
        "knowledge_search", "document_retrieval", "sop_lookup",
    ],
    IntentType.INCIDENT_RESPONSE: [
        "incident_detection", "incident_response",
        "incident_escalation",
    ],
    IntentType.EVACUATION: [
        "evacuation_transport", "crowd_management", "rerouting",
    ],
    IntentType.WEATHER_ADVISORY: [
        "weather_monitoring", "weather_advisory",
        "severe_weather",
    ],
    IntentType.SECURITY: [
        "incident_detection", "incident_escalation",
    ],
    IntentType.OPERATIONAL: [
        "knowledge_search", "multi_step_reasoning",
        "strategic_planning",
    ],
}


class ExecutionPlanner:
    """Generates and replans execution plans using the agent and tool registries."""

    def __init__(
        self,
        agent_registry: AgentRegistry,
        tool_registry: ToolRegistry,
        dependency_resolver: DependencyResolver,
        strategy_selector: StrategySelector,
    ) -> None:
        self._agent_registry = agent_registry
        self._tool_registry = tool_registry
        self._resolver = dependency_resolver
        self._strategy_selector = strategy_selector

    async def plan(
        self,
        request: OrchestratorRequest,
        context: dict,
    ) -> Result[ExecutionPlan]:
        try:
            capabilities = await self._analyze_intent(request)
            if not capabilities:
                return Failure(
                    error_code="NO_CAPABILITIES_DETECTED",
                    message=(
                        "Unable to determine required"
                        " capabilities from request"
                    ),
                )

            criteria = AgentSelectorCriteria(
                required_capabilities=capabilities,
                max_cost=None,
                max_latency_ms=request.timeout_seconds * 1000,
            )
            agents = await self._select_agents(
                capabilities, criteria,
            )
            if not agents:
                return Failure(
                    error_code="NO_AGENTS_AVAILABLE",
                    message=(
                        "No agents available for the"
                        " required capabilities"
                    ),
                    details={
                        "required_capabilities": capabilities,
                    },
                )

            steps = self._build_steps(
                agents, request, context,
            )
            steps = self._assign_priorities(steps)

            dependencies = self._build_dependency_graph(steps)
            validation = await self._resolver.validate_dag(
                steps, dependencies,
            )
            if isinstance(validation, Failure):
                return Failure(
                    error_code=validation.error_code,
                    message=validation.message,
                    details=validation.details,
                )

            strategy = self._strategy_selector.select_strategy(
                steps, dependencies,
                {
                    "request_type": request.request_type.value,
                    "priority": request.priority,
                    "timeout": request.timeout_seconds,
                },
            )
            timeout = (
                self._strategy_selector.estimate_optimal_timeout(
                    steps, strategy,
                )
            )

            plan_id = uuid.uuid4()
            plan = ExecutionPlan(
                plan_id=plan_id,
                strategy=strategy,
                steps=steps,
                dependencies=dependencies,
                timeout_seconds=timeout,
            )

            logger.info(
                "Plan %s generated: %d steps, strategy=%s,"
                " timeout=%.1fs",
                plan_id, len(steps), strategy.value, timeout,
            )
            return Success(plan)

        except PlannerError as exc:
            return Failure(
                error_code="PLANNING_FAILED",
                message=str(exc.message),
                details=exc.details,
            )

    async def replan(
        self,
        plan: ExecutionPlan,
        failure_step: UUID,
        error: str,
    ) -> Result[ExecutionPlan]:
        logger.warning(
            "Replanning after step %s failed: %s",
            failure_step, error,
        )

        fallback_strategy = (
            self._strategy_selector.suggest_fallback(
                plan.strategy,
            )
        )
        remaining_steps = [
            s for s in plan.steps
            if s.step_id != failure_step
        ]

        if not remaining_steps:
            return Failure(
                error_code="NO_REMAINING_STEPS",
                message=(
                    "All steps have failed or been removed"
                ),
                details={
                    "failed_step": str(failure_step),
                    "error": error,
                },
            )

        adjusted_dependencies = {
            sid: [d for d in deps if d != failure_step]
            for sid, deps in plan.dependencies.items()
            if sid != failure_step
        }

        validation = await self._resolver.validate_dag(
            remaining_steps, adjusted_dependencies,
        )
        if isinstance(validation, Failure):
            return Failure(
                error_code=validation.error_code,
                message=(
                    f"Replan validation failed:"
                    f" {validation.message}"
                ),
                details=validation.details,
            )

        timeout = (
            self._strategy_selector.estimate_optimal_timeout(
                remaining_steps, fallback_strategy,
            )
        )

        new_plan = ExecutionPlan(
            plan_id=uuid.uuid4(),
            strategy=fallback_strategy,
            steps=remaining_steps,
            dependencies=adjusted_dependencies,
            timeout_seconds=timeout,
        )

        logger.info(
            "Replan %s: %d steps, strategy=%s, timeout=%.1fs",
            new_plan.plan_id, len(remaining_steps),
            fallback_strategy.value, timeout,
        )
        return Success(new_plan)

    async def _analyze_intent(
        self, request: OrchestratorRequest,
    ) -> list[str]:
        if request.intent is not None:
            return _INTENT_TO_CAPABILITIES.get(
                request.intent, [],
            )

        query_lower = request.query.lower()
        detected: list[str] = []
        for intent, capabilities in (
            _INTENT_TO_CAPABILITIES.items()
        ):
            intent_words = intent.value.split("_")
            if any(
                word in query_lower for word in intent_words
            ):
                detected.extend(capabilities)

        if not detected:
            return [
                "knowledge_search",
                "multi_step_reasoning",
            ]

        return list(dict.fromkeys(detected))

    async def _select_agents(
        self,
        capabilities: list[str],
        criteria: AgentSelectorCriteria,
    ) -> list[RegisteredAgent]:
        candidates = await self._agent_registry.find_agents(
            criteria,
        )
        if not candidates:
            candidates = (
                await self._agent_registry.get_healthy_agents()
            )

        scored: list[tuple[float, RegisteredAgent]] = []
        for agent in candidates:
            agent_caps = {
                c.name for c in agent.metadata.capabilities
            }
            overlap = len(agent_caps & set(capabilities))
            score = (
                (overlap * 10)
                + agent.metadata.priority
                - agent.metadata.cost_per_invocation * 50
            )
            scored.append((score, agent))

        scored.sort(key=lambda x: x[0], reverse=True)
        limit = len(capabilities) + 2
        return [agent for _, agent in scored[:limit]]

    def _build_steps(
        self,
        agents: list[RegisteredAgent],
        request: OrchestratorRequest,
        context: dict,
    ) -> list[ExecutionStep]:
        steps: list[ExecutionStep] = []
        for idx, agent in enumerate(agents):
            matching_caps = [
                c.name
                for c in agent.metadata.capabilities
                if any(
                    keyword in request.query.lower()
                    for keyword in c.name.split("_")
                )
            ]
            action = (
                matching_caps[0]
                if matching_caps
                else agent.metadata.supported_actions[0]
            )

            step = ExecutionStep(
                step_id=uuid.uuid4(),
                agent_id=agent.metadata.agent_id,
                agent_name=agent.metadata.name,
                action=action,
                parameters={
                    "query": request.query,
                    "venue_id": (
                        str(request.venue_id)
                        if request.venue_id else None
                    ),
                    "zone_id": (
                        str(request.zone_id)
                        if request.zone_id else None
                    ),
                    "context": context,
                },
                timeout_seconds=(
                    agent.metadata.avg_latency_ms / 1000.0 * 3
                ),
                retry_policy=RetryPolicy(
                    max_retries=(
                        2 if agent.metadata.priority >= 7
                        else 1
                    ),
                    backoff_seconds=1.0,
                    backoff_multiplier=2.0,
                ),
                is_parallel=idx > 0,
                order=idx,
            )
            steps.append(step)
        return steps

    def _assign_priorities(
        self, steps: list[ExecutionStep],
    ) -> list[ExecutionStep]:
        return [
            step.model_copy(update={"order": idx})
            for idx, step in enumerate(
                sorted(steps, key=lambda s: s.order)
            )
        ]

    def _build_dependency_graph(
        self,
        steps: list[ExecutionStep],
    ) -> dict[UUID, list[UUID]]:
        if not steps:
            return {}

        sorted_steps = sorted(
            steps, key=lambda s: s.order,
        )
        dependencies: dict[UUID, list[UUID]] = {}

        for idx, step in enumerate(sorted_steps):
            if step.depends_on:
                dependencies[step.step_id] = list(
                    step.depends_on,
                )
            elif idx > 0:
                dependencies[step.step_id] = [
                    sorted_steps[idx - 1].step_id,
                ]
            else:
                dependencies[step.step_id] = []

        return dependencies
