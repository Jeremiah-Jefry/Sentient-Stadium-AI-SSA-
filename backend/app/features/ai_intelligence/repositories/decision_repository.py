"""Decision repository — data access for intervention decision history."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.ai_intelligence.models.decision import DecisionHistory
from app.features.ai_intelligence.models.enums import DecisionStatus
from app.shared.result import Failure, Result, Success

logger = logging.getLogger(__name__)


class DecisionRepository:
    """Handles all database operations for DecisionHistory."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, decision: DecisionHistory) -> Result[DecisionHistory]:
        """Persist a single decision record."""
        self._session.add(decision)
        await self._session.flush()
        logger.debug("Decision saved: %s", decision.id)
        return Success(decision)

    async def get_by_id(
        self, decision_id: uuid.UUID,
    ) -> Result[DecisionHistory | None]:
        """Fetch a single decision by UUID."""
        stmt = select(DecisionHistory).where(DecisionHistory.id == decision_id)
        result = await self._session.execute(stmt)
        return Success(result.scalar_one_or_none())

    async def get_by_venue(
        self,
        venue_id: uuid.UUID,
        status: str | None = None,
        intervention_type: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Result[tuple[list[DecisionHistory], int]]:
        """Query decisions for a venue with optional filters and pagination."""
        base_query = select(DecisionHistory).where(
            DecisionHistory.venue_id == venue_id,
        )

        if status is not None:
            base_query = base_query.where(DecisionHistory.decision_status == status)
        if intervention_type is not None:
            base_query = base_query.where(
                DecisionHistory.intervention_type == intervention_type,
            )

        count_stmt = select(func.count()).select_from(base_query.subquery())
        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar_one()

        paginated = (
            base_query
            .order_by(DecisionHistory.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self._session.execute(paginated)
        decisions = list(result.scalars().all())
        return Success((decisions, total))

    async def get_pending(self) -> Result[list[DecisionHistory]]:
        """Fetch all decisions in CANDIDATE or SIMULATED status."""
        pending_statuses = [
            DecisionStatus.CANDIDATE.value,
            DecisionStatus.SIMULATED.value,
        ]
        stmt = (
            select(DecisionHistory)
            .where(DecisionHistory.decision_status.in_(pending_statuses))
            .order_by(DecisionHistory.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return Success(list(result.scalars().all()))

    async def update_status(
        self, decision_id: uuid.UUID, status: str,
    ) -> Result[DecisionHistory]:
        """Update the status of a decision, recording lifecycle transitions."""
        stmt = select(DecisionHistory).where(DecisionHistory.id == decision_id)
        result = await self._session.execute(stmt)
        decision = result.scalar_one_or_none()

        if decision is None:
            return Failure(
                error_code="DECISION_NOT_FOUND",
                message=f"Decision {decision_id} not found",
            )

        now = datetime.now(timezone.utc)
        previous_status = decision.decision_status
        decision.decision_status = status

        if status == DecisionStatus.PUBLISHED.value:
            decision.published_at = now
        elif status == DecisionStatus.EXECUTED.value:
            decision.executed_at = now
        elif status == DecisionStatus.EXPIRED.value:
            decision.expires_at = now

        await self._session.flush()
        logger.info(
            "Decision %s status: %s -> %s",
            decision_id, previous_status, status,
        )
        return Success(decision)
