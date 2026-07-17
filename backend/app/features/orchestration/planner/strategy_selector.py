"""Strategy selector — chooses the optimal execution strategy for a plan."""

from __future__ import annotations

import logging
from uuid import UUID

from app.features.orchestration.dto.execution import ExecutionStep
from app.features.orchestration.models.enums import ExecutionStrategy

logger = logging.getLogger(__name__)

_CONDITIONAL_KEYWORDS = frozenset({"if", "when", "unless", "conditional", "branch"})
_LOOP_KEYWORDS = frozenset({"loop", "repeat", "iterate", "for_each", "until"})
_DYNAMIC_KEYWORDS = frozenset({"dynamic", "runtime", "adaptive", "decide", "choose"})


class StrategySelector:
    """Analyzes execution steps and constraints to recommend a strategy."""

    def __init__(self) -> None:
        pass

    def select_strategy(
        self,
        steps: list[ExecutionStep],
        dependencies: dict[UUID, list[UUID]],
        constraints: dict,
    ) -> ExecutionStrategy:
        if not steps:
            return ExecutionStrategy.SEQUENTIAL

        constraint_text = " ".join(str(v) for v in constraints.values()).lower()
        all_actions = " ".join(s.action.lower() for s in steps)

        if any(kw in constraint_text or kw in all_actions for kw in _DYNAMIC_KEYWORDS):
            return ExecutionStrategy.DYNAMIC

        if any(kw in constraint_text or kw in all_actions for kw in _LOOP_KEYWORDS):
            return ExecutionStrategy.LOOP

        if any(kw in constraint_text or kw in all_actions for kw in _CONDITIONAL_KEYWORDS):
            return ExecutionStrategy.CONDITIONAL

        if not dependencies or all(len(deps) == 0 for deps in dependencies.values()):
            return ExecutionStrategy.PARALLEL

        has_any_dependency = any(len(deps) > 0 for deps in dependencies.values())
        all_chain = self._is_linear_chain(steps, dependencies)

        if all_chain:
            return ExecutionStrategy.SEQUENTIAL

        if has_any_dependency:
            return ExecutionStrategy.MIXED

        return ExecutionStrategy.PARALLEL

    def estimate_optimal_timeout(
        self,
        steps: list[ExecutionStep],
        strategy: ExecutionStrategy,
    ) -> float:
        if not steps:
            return 30.0

        timeouts = [s.timeout_seconds for s in steps]
        max_timeout = max(timeouts)
        sum_timeout = sum(timeouts)

        if strategy == ExecutionStrategy.PARALLEL:
            buffer = max_timeout * 0.25
            return max_timeout + buffer

        if strategy == ExecutionStrategy.SEQUENTIAL:
            buffer = sum_timeout * 0.15
            return sum_timeout + buffer

        if strategy == ExecutionStrategy.MIXED:
            return max_timeout * 1.5 + sum_timeout * 0.3

        buffer = max_timeout * 0.30
        return sum_timeout + buffer

    def suggest_fallback(self, main_strategy: ExecutionStrategy) -> ExecutionStrategy:
        fallback_map: dict[ExecutionStrategy, ExecutionStrategy] = {
            ExecutionStrategy.PARALLEL: ExecutionStrategy.SEQUENTIAL,
            ExecutionStrategy.SEQUENTIAL: ExecutionStrategy.PARALLEL,
            ExecutionStrategy.MIXED: ExecutionStrategy.SEQUENTIAL,
            ExecutionStrategy.CONDITIONAL: ExecutionStrategy.SEQUENTIAL,
            ExecutionStrategy.LOOP: ExecutionStrategy.SEQUENTIAL,
            ExecutionStrategy.DYNAMIC: ExecutionStrategy.MIXED,
        }
        return fallback_map.get(main_strategy, ExecutionStrategy.SEQUENTIAL)

    def _is_linear_chain(
        self,
        steps: list[ExecutionStep],
        dependencies: dict[UUID, list[UUID]],
    ) -> bool:
        if len(steps) <= 1:
            return True

        max_deps = max(len(deps) for deps in dependencies.values()) if dependencies else 0
        if max_deps > 1:
            return False

        nodes_with_deps = sum(1 for deps in dependencies.values() if len(deps) > 0)
        return nodes_with_deps == len(steps) - 1
