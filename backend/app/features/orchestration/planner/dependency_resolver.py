"""DAG-based dependency resolver — topological sort and execution wave grouping."""

from __future__ import annotations

import logging
from collections import defaultdict, deque
from uuid import UUID

from app.features.orchestration.dto.execution import ExecutionStep
from app.features.orchestration.exceptions import PlannerError
from app.shared.result import Failure, Result, Success

logger = logging.getLogger(__name__)


class DependencyResolver:
    """Resolves execution step dependencies using Kahn's algorithm for topological sort."""

    def __init__(self) -> None:
        pass

    async def resolve(
        self,
        steps: list[ExecutionStep],
        dependencies: dict[UUID, list[UUID]],
    ) -> Result[list[list[ExecutionStep]]]:
        validation = await self.validate_dag(steps, dependencies)
        if isinstance(validation, Failure):
            return Failure(
                error_code=validation.error_code,
                message=validation.message,
                details=validation.details,
            )

        waves = await self.get_execution_waves(steps, dependencies)
        return Success(waves)

    async def validate_dag(
        self,
        steps: list[ExecutionStep],
        dependencies: dict[UUID, list[UUID]],
    ) -> Result[None]:
        step_ids = {s.step_id for s in steps}

        for step_id, deps in dependencies.items():
            if step_id not in step_ids:
                return Failure(
                    error_code="UNKNOWN_STEP",
                    message=f"Dependency references unknown step '{step_id}'",
                    details={"step_id": str(step_id)},
                )
            for dep_id in deps:
                if dep_id not in step_ids:
                    return Failure(
                        error_code="UNKNOWN_DEPENDENCY",
                        message=f"Step '{step_id}' depends on unknown step '{dep_id}'",
                        details={"step_id": str(step_id), "dependency_id": str(dep_id)},
                    )

        in_degree: dict[UUID, int] = {s.step_id: 0 for s in steps}
        for step_id, deps in dependencies.items():
            in_degree[step_id] = len(deps)

        queue: deque[UUID] = deque()
        for step_id, degree in in_degree.items():
            if degree == 0:
                queue.append(step_id)

        visited = 0
        while queue:
            current = queue.popleft()
            visited += 1
            for step_id, deps in dependencies.items():
                if current in deps:
                    in_degree[step_id] -= 1
                    if in_degree[step_id] == 0:
                        queue.append(step_id)

        if visited != len(steps):
            cycle_steps = [str(sid) for sid, deg in in_degree.items() if deg > 0]
            raise PlannerError(
                message="Dependency cycle detected",
                details={"steps_in_cycle": cycle_steps},
            )

        return Success(None)

    async def get_execution_waves(
        self,
        steps: list[ExecutionStep],
        dependencies: dict[UUID, list[UUID]],
    ) -> list[list[ExecutionStep]]:
        step_map = {s.step_id: s for s in steps}
        in_degree: dict[UUID, int] = {s.step_id: 0 for s in steps}
        reverse_deps: dict[UUID, list[UUID]] = defaultdict(list)

        for step_id, deps in dependencies.items():
            in_degree[step_id] = len(deps)
            for dep_id in deps:
                reverse_deps[dep_id].append(step_id)

        queue: deque[UUID] = deque()
        for step_id, degree in in_degree.items():
            if degree == 0:
                queue.append(step_id)

        waves: list[list[ExecutionStep]] = []
        while queue:
            wave: list[ExecutionStep] = []
            next_queue: deque[UUID] = deque()
            while queue:
                step_id = queue.popleft()
                wave.append(step_map[step_id])
                for dependent_id in reverse_deps.get(step_id, []):
                    in_degree[dependent_id] -= 1
                    if in_degree[dependent_id] == 0:
                        next_queue.append(dependent_id)
            waves.append(sorted(wave, key=lambda s: s.order))
            queue = next_queue

        return waves

    async def detect_critical_path(
        self,
        steps: list[ExecutionStep],
        dependencies: dict[UUID, list[UUID]],
    ) -> list[ExecutionStep]:
        step_map = {s.step_id: s for s in steps}
        longest: dict[UUID, float] = {s.step_id: 0.0 for s in steps}
        predecessor: dict[UUID, UUID | None] = {s.step_id: None for s in steps}

        sorted_ids = await self._topological_order(steps, dependencies)
        for step_id in sorted_ids:
            for dep_id in dependencies.get(step_id, []):
                candidate = longest[dep_id] + step_map[dep_id].timeout_seconds
                if candidate > longest[step_id]:
                    longest[step_id] = candidate
                    predecessor[step_id] = dep_id

        end_node = max(longest, key=lambda k: longest[k])
        path: list[UUID] = []
        current: UUID | None = end_node
        while current is not None:
            path.append(current)
            current = predecessor[current]
        path.reverse()

        return [step_map[sid] for sid in path]

    async def estimate_duration(
        self,
        steps: list[ExecutionStep],
        dependencies: dict[UUID, list[UUID]],
    ) -> float:
        critical_path = await self.detect_critical_path(steps, dependencies)
        return sum(s.timeout_seconds for s in critical_path)

    async def _topological_order(
        self,
        steps: list[ExecutionStep],
        dependencies: dict[UUID, list[UUID]],
    ) -> list[UUID]:
        in_degree: dict[UUID, int] = {s.step_id: 0 for s in steps}
        for step_id, deps in dependencies.items():
            in_degree[step_id] = len(deps)

        queue: deque[UUID] = deque()
        for step_id, degree in in_degree.items():
            if degree == 0:
                queue.append(step_id)

        result: list[UUID] = []
        while queue:
            current = queue.popleft()
            result.append(current)
            for step_id, deps in dependencies.items():
                if current in deps:
                    in_degree[step_id] -= 1
                    if in_degree[step_id] == 0:
                        queue.append(step_id)
        return result
