"""Repository for ExecutionHistory, ExecutionPlan, and ExecutionStepRecord."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.orchestration.models.database import (
    ExecutionHistory,
    ExecutionPlan,
    ExecutionStepRecord,
)
from app.shared.result import Failure, Result, Success

logger = logging.getLogger(__name__)


class ExecutionRepository:
    """Handles all database operations for orchestration execution records."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── ExecutionHistory ──────────────────────────────────────────────

    async def save(self, execution: ExecutionHistory) -> Result[ExecutionHistory]:
        self._session.add(execution)
        await self._session.flush()
        logger.debug("ExecutionHistory saved: %s", execution.id)
        return Success(execution)

    async def save_many(
        self, executions: list[ExecutionHistory],
    ) -> Result[list[ExecutionHistory]]:
        self._session.add_all(executions)
        await self._session.flush()
        logger.debug("Batch saved %d ExecutionHistory records", len(executions))
        return Success(executions)

    async def get_by_id(
        self, execution_id: uuid.UUID,
    ) -> Result[ExecutionHistory | None]:
        stmt = select(ExecutionHistory).where(ExecutionHistory.id == execution_id)
        result = await self._session.execute(stmt)
        return Success(result.scalar_one_or_none())

    async def get_by_request_id(
        self, request_id: uuid.UUID,
    ) -> Result[list[ExecutionHistory]]:
        stmt = (
            select(ExecutionHistory)
            .where(ExecutionHistory.request_id == request_id)
            .order_by(ExecutionHistory.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return Success(list(result.scalars().all()))

    async def get_by_status(
        self,
        status: str,
        page: int = 1,
        page_size: int = 50,
    ) -> Result[tuple[list[ExecutionHistory], int]]:
        base_query = select(ExecutionHistory).where(
            ExecutionHistory.status == status,
        )

        count_stmt = select(func.count()).select_from(base_query.subquery())
        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar_one()

        paginated = (
            base_query
            .order_by(ExecutionHistory.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self._session.execute(paginated)
        executions = list(result.scalars().all())
        return Success((executions, total))

    async def get_recent(
        self, limit: int = 20,
    ) -> Result[list[ExecutionHistory]]:
        stmt = (
            select(ExecutionHistory)
            .order_by(ExecutionHistory.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return Success(list(result.scalars().all()))

    async def update_status(
        self, execution_id: uuid.UUID, status: str,
    ) -> Result[ExecutionHistory]:
        stmt = select(ExecutionHistory).where(ExecutionHistory.id == execution_id)
        result = await self._session.execute(stmt)
        execution = result.scalar_one_or_none()

        if execution is None:
            return Failure(
                error_code="EXECUTION_NOT_FOUND",
                message=f"Execution {execution_id} not found",
            )

        execution.status = status
        await self._session.flush()
        logger.debug("Execution %s status updated to %s", execution_id, status)
        return Success(execution)

    async def get_execution_stats(self) -> Result[dict]:
        total_stmt = select(func.count()).select_from(ExecutionHistory)
        total_result = await self._session.execute(total_stmt)
        total = total_result.scalar_one()

        status_stmt = (
            select(ExecutionHistory.status, func.count())
            .group_by(ExecutionHistory.status)
        )
        status_result = await self._session.execute(status_stmt)
        status_counts = dict(status_result.all())

        avg_duration_stmt = select(
            func.avg(ExecutionHistory.total_duration_ms),
        ).where(ExecutionHistory.total_duration_ms.isnot(None))
        avg_result = await self._session.execute(avg_duration_stmt)
        avg_duration = avg_result.scalar_one()

        avg_confidence_stmt = select(
            func.avg(ExecutionHistory.confidence),
        ).where(ExecutionHistory.confidence.isnot(None))
        conf_result = await self._session.execute(avg_confidence_stmt)
        avg_confidence = conf_result.scalar_one()

        return Success({
            "total_executions": total,
            "status_distribution": status_counts,
            "avg_duration_ms": round(float(avg_duration or 0), 2),
            "avg_confidence": round(float(avg_confidence or 0), 4),
        })

    # ── ExecutionPlan ─────────────────────────────────────────────────

    async def save_plan(self, plan: ExecutionPlan) -> Result[ExecutionPlan]:
        self._session.add(plan)
        await self._session.flush()
        logger.debug("ExecutionPlan saved: %s", plan.id)
        return Success(plan)

    async def get_plan_by_id(
        self, plan_id: uuid.UUID,
    ) -> Result[ExecutionPlan | None]:
        stmt = select(ExecutionPlan).where(ExecutionPlan.id == plan_id)
        result = await self._session.execute(stmt)
        return Success(result.scalar_one_or_none())

    async def get_plans_by_request_id(
        self, request_id: uuid.UUID,
    ) -> Result[list[ExecutionPlan]]:
        stmt = (
            select(ExecutionPlan)
            .where(ExecutionPlan.request_id == request_id)
            .order_by(ExecutionPlan.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return Success(list(result.scalars().all()))

    async def update_plan_status(
        self, plan_id: uuid.UUID, status: str,
    ) -> Result[ExecutionPlan]:
        stmt = select(ExecutionPlan).where(ExecutionPlan.id == plan_id)
        result = await self._session.execute(stmt)
        plan = result.scalar_one_or_none()

        if plan is None:
            return Failure(
                error_code="PLAN_NOT_FOUND",
                message=f"Plan {plan_id} not found",
            )

        plan.status = status
        await self._session.flush()
        logger.debug("ExecutionPlan %s status updated to %s", plan_id, status)
        return Success(plan)

    # ── ExecutionStepRecord ───────────────────────────────────────────

    async def save_step(self, step: ExecutionStepRecord) -> Result[ExecutionStepRecord]:
        self._session.add(step)
        await self._session.flush()
        logger.debug("ExecutionStepRecord saved: %s", step.id)
        return Success(step)

    async def save_steps(
        self, steps: list[ExecutionStepRecord],
    ) -> Result[list[ExecutionStepRecord]]:
        self._session.add_all(steps)
        await self._session.flush()
        logger.debug("Batch saved %d ExecutionStepRecord records", len(steps))
        return Success(steps)

    async def get_steps_by_execution_id(
        self, execution_id: uuid.UUID,
    ) -> Result[list[ExecutionStepRecord]]:
        stmt = (
            select(ExecutionStepRecord)
            .where(ExecutionStepRecord.execution_id == execution_id)
            .order_by(ExecutionStepRecord.created_at.asc())
        )
        result = await self._session.execute(stmt)
        return Success(list(result.scalars().all()))

    async def get_steps_by_agent_id(
        self, agent_id: uuid.UUID, limit: int = 50,
    ) -> Result[list[ExecutionStepRecord]]:
        stmt = (
            select(ExecutionStepRecord)
            .where(ExecutionStepRecord.agent_id == agent_id)
            .order_by(ExecutionStepRecord.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return Success(list(result.scalars().all()))
