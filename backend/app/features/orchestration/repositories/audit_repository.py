"""Repository for OrchestrationAuditLog records."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.orchestration.models.database import OrchestrationAuditLog
from app.shared.result import Result, Success

logger = logging.getLogger(__name__)


class AuditRepository:
    """Handles all database operations for orchestration audit logs."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, entry: OrchestrationAuditLog) -> Result[OrchestrationAuditLog]:
        self._session.add(entry)
        await self._session.flush()
        logger.debug("AuditLog saved: %s", entry.id)
        return Success(entry)

    async def save_many(
        self, entries: list[OrchestrationAuditLog],
    ) -> Result[list[OrchestrationAuditLog]]:
        self._session.add_all(entries)
        await self._session.flush()
        logger.debug("Batch saved %d AuditLog records", len(entries))
        return Success(entries)

    async def get_by_execution_id(
        self, execution_id: uuid.UUID,
    ) -> Result[list[OrchestrationAuditLog]]:
        stmt = (
            select(OrchestrationAuditLog)
            .where(OrchestrationAuditLog.execution_id == execution_id)
            .order_by(OrchestrationAuditLog.created_at.asc())
        )
        result = await self._session.execute(stmt)
        return Success(list(result.scalars().all()))

    async def get_by_event_type(
        self,
        event_type: str,
        page: int = 1,
        page_size: int = 50,
    ) -> Result[tuple[list[OrchestrationAuditLog], int]]:
        base_query = select(OrchestrationAuditLog).where(
            OrchestrationAuditLog.event_type == event_type,
        )

        count_stmt = select(func.count()).select_from(base_query.subquery())
        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar_one()

        paginated = (
            base_query
            .order_by(OrchestrationAuditLog.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self._session.execute(paginated)
        entries = list(result.scalars().all())
        return Success((entries, total))

    async def get_audit_summary(self) -> Result[dict]:
        event_stmt = (
            select(OrchestrationAuditLog.event_type, func.count())
            .group_by(OrchestrationAuditLog.event_type)
        )
        event_result = await self._session.execute(event_stmt)
        event_counts = dict(event_result.all())

        total_stmt = select(func.count()).select_from(OrchestrationAuditLog)
        total_result = await self._session.execute(total_stmt)
        total = total_result.scalar_one()

        avg_risk_stmt = select(
            func.avg(OrchestrationAuditLog.risk_score),
        ).where(OrchestrationAuditLog.risk_score > 0)
        avg_risk_result = await self._session.execute(avg_risk_stmt)
        avg_risk_score = avg_risk_result.scalar_one()

        return Success({
            "total_events": total,
            "event_type_distribution": event_counts,
            "avg_risk_score": round(float(avg_risk_score or 0), 4),
        })
