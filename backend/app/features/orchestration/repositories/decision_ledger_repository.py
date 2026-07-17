"""Repository for DecisionLedger records."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.orchestration.models.database import DecisionLedger
from app.shared.result import Result, Success

logger = logging.getLogger(__name__)


class DecisionLedgerRepository:
    """Handles all database operations for decision ledger entries."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, entry: DecisionLedger) -> Result[DecisionLedger]:
        self._session.add(entry)
        await self._session.flush()
        logger.debug("DecisionLedger entry saved: %s", entry.id)
        return Success(entry)

    async def get_by_id(
        self, entry_id: uuid.UUID,
    ) -> Result[DecisionLedger | None]:
        stmt = select(DecisionLedger).where(DecisionLedger.id == entry_id)
        result = await self._session.execute(stmt)
        return Success(result.scalar_one_or_none())

    async def get_by_execution_id(
        self, execution_id: uuid.UUID,
    ) -> Result[list[DecisionLedger]]:
        stmt = (
            select(DecisionLedger)
            .where(DecisionLedger.execution_id == execution_id)
            .order_by(DecisionLedger.created_at.asc())
        )
        result = await self._session.execute(stmt)
        return Success(list(result.scalars().all()))

    async def get_by_request_id(
        self, request_id: uuid.UUID,
    ) -> Result[list[DecisionLedger]]:
        stmt = (
            select(DecisionLedger)
            .where(DecisionLedger.request_id == request_id)
            .order_by(DecisionLedger.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return Success(list(result.scalars().all()))

    async def get_recent_decisions(
        self,
        safety_level: str | None = None,
        min_confidence: float | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Result[tuple[list[DecisionLedger], int]]:
        base_query = select(DecisionLedger)

        if safety_level is not None:
            base_query = base_query.where(
                DecisionLedger.safety_level == safety_level,
            )
        if min_confidence is not None:
            base_query = base_query.where(
                DecisionLedger.confidence >= min_confidence,
            )

        count_stmt = select(func.count()).select_from(base_query.subquery())
        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar_one()

        paginated = (
            base_query
            .order_by(DecisionLedger.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self._session.execute(paginated)
        entries = list(result.scalars().all())
        return Success((entries, total))

    async def get_decision_stats(self) -> Result[dict]:
        total_stmt = select(func.count()).select_from(DecisionLedger)
        total_result = await self._session.execute(total_stmt)
        total = total_result.scalar_one()

        avg_conf_stmt = select(
            func.avg(DecisionLedger.confidence),
        ).where(DecisionLedger.confidence.isnot(None))
        avg_conf_result = await self._session.execute(avg_conf_stmt)
        avg_confidence = avg_conf_result.scalar_one()

        safety_stmt = (
            select(DecisionLedger.safety_level, func.count())
            .where(DecisionLedger.safety_level.isnot(None))
            .group_by(DecisionLedger.safety_level)
        )
        safety_result = await self._session.execute(safety_stmt)
        safety_distribution = dict(safety_result.all())

        return Success({
            "total_decisions": total,
            "avg_confidence": round(float(avg_confidence or 0), 4),
            "safety_level_distribution": safety_distribution,
        })
