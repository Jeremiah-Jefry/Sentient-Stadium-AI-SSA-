"""Tests for DependencyResolver — DAG validation, topological sort, and execution wave grouping."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from app.features.orchestration.dto.execution import ExecutionStep
from app.features.orchestration.exceptions import PlannerError
from app.features.orchestration.planner.dependency_resolver import DependencyResolver
from app.shared.result import Failure, Success


def _make_step(
    step_id: UUID,
    name: str = "step",
    order: int = 0,
    timeout: float = 5.0,
    agent_id: UUID | None = None,
) -> ExecutionStep:
    return ExecutionStep(
        step_id=step_id,
        agent_id=agent_id or uuid4(),
        agent_name=f"Agent for {name}",
        action=name,
        timeout_seconds=timeout,
        order=order,
    )


@pytest.fixture
def resolver() -> DependencyResolver:
    return DependencyResolver()


class TestDependencyResolver:

    @pytest.mark.asyncio
    async def test_resolve_parallel_steps(self, resolver: DependencyResolver) -> None:
        a_id, b_id, c_id = uuid4(), uuid4(), uuid4()
        steps = [
            _make_step(a_id, "step_a", order=0),
            _make_step(b_id, "step_b", order=1),
            _make_step(c_id, "step_c", order=2),
        ]
        dependencies = {a_id: [], b_id: [], c_id: []}

        result = await resolver.resolve(steps, dependencies)
        assert isinstance(result, Success)
        waves = result.value
        assert len(waves) == 1
        assert len(waves[0]) == 3

    @pytest.mark.asyncio
    async def test_resolve_linear_chain(self, resolver: DependencyResolver) -> None:
        a_id, b_id, c_id = uuid4(), uuid4(), uuid4()
        steps = [
            _make_step(a_id, "step_a", order=0),
            _make_step(b_id, "step_b", order=1),
            _make_step(c_id, "step_c", order=2),
        ]
        dependencies = {
            a_id: [],
            b_id: [a_id],
            c_id: [b_id],
        }

        result = await resolver.resolve(steps, dependencies)
        assert isinstance(result, Success)
        waves = result.value
        assert len(waves) == 3
        assert waves[0][0].step_id == a_id
        assert waves[1][0].step_id == b_id
        assert waves[2][0].step_id == c_id

    @pytest.mark.asyncio
    async def test_resolve_mixed(self, resolver: DependencyResolver) -> None:
        a_id, b_id, c_id, d_id = uuid4(), uuid4(), uuid4(), uuid4()
        steps = [
            _make_step(a_id, "step_a", order=0),
            _make_step(b_id, "step_b", order=1),
            _make_step(c_id, "step_c", order=2),
            _make_step(d_id, "step_d", order=3),
        ]
        dependencies = {
            a_id: [],
            b_id: [],
            c_id: [a_id, b_id],
            d_id: [c_id],
        }

        result = await resolver.resolve(steps, dependencies)
        assert isinstance(result, Success)
        waves = result.value
        assert len(waves) == 3
        wave0_ids = {s.step_id for s in waves[0]}
        assert a_id in wave0_ids
        assert b_id in wave0_ids
        assert waves[1][0].step_id == c_id
        assert waves[2][0].step_id == d_id

    @pytest.mark.asyncio
    async def test_detect_cycle(self, resolver: DependencyResolver) -> None:
        a_id, b_id = uuid4(), uuid4()
        steps = [
            _make_step(a_id, "step_a", order=0),
            _make_step(b_id, "step_b", order=1),
        ]
        dependencies = {
            a_id: [b_id],
            b_id: [a_id],
        }

        with pytest.raises(PlannerError) as exc_info:
            await resolver.resolve(steps, dependencies)
        assert "cycle" in str(exc_info.value.message).lower()

    @pytest.mark.asyncio
    async def test_validate_dag_unknown_step(self, resolver: DependencyResolver) -> None:
        a_id = uuid4()
        steps = [_make_step(a_id, "step_a")]
        dependencies = {uuid4(): [a_id]}

        result = await resolver.validate_dag(steps, dependencies)
        assert isinstance(result, Failure)
        assert result.error_code == "UNKNOWN_STEP"

    @pytest.mark.asyncio
    async def test_validate_dag_unknown_dependency(self, resolver: DependencyResolver) -> None:
        a_id = uuid4()
        steps = [_make_step(a_id, "step_a")]
        dependencies = {a_id: [uuid4()]}

        result = await resolver.validate_dag(steps, dependencies)
        assert isinstance(result, Failure)
        assert result.error_code == "UNKNOWN_DEPENDENCY"

    @pytest.mark.asyncio
    async def test_get_execution_waves_single_step(self, resolver: DependencyResolver) -> None:
        a_id = uuid4()
        steps = [_make_step(a_id, "step_a")]
        dependencies = {a_id: []}

        waves = await resolver.get_execution_waves(steps, dependencies)
        assert len(waves) == 1
        assert len(waves[0]) == 1

    @pytest.mark.asyncio
    async def test_estimate_duration(self, resolver: DependencyResolver) -> None:
        a_id, b_id = uuid4(), uuid4()
        steps = [
            _make_step(a_id, "step_a", timeout=10.0),
            _make_step(b_id, "step_b", timeout=5.0),
        ]
        dependencies = {a_id: [], b_id: [a_id]}

        duration = await resolver.estimate_duration(steps, dependencies)
        assert duration == 15.0

    @pytest.mark.asyncio
    async def test_detect_critical_path(self, resolver: DependencyResolver) -> None:
        a_id, b_id, c_id = uuid4(), uuid4(), uuid4()
        steps = [
            _make_step(a_id, "fast", timeout=5.0),
            _make_step(b_id, "slow", timeout=20.0),
            _make_step(c_id, "merge", timeout=3.0),
        ]
        dependencies = {
            a_id: [],
            b_id: [],
            c_id: [a_id, b_id],
        }

        path = await resolver.detect_critical_path(steps, dependencies)
        path_ids = [s.step_id for s in path]
        assert b_id in path_ids
