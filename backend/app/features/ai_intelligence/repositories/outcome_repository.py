"""Outcome repository — data access for historical intervention outcomes."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.ai_intelligence.models.historical_outcome import HistoricalOutcome
from app.shared.result import Result, Success

logger = logging.getLogger(__name__)


class OutcomeRepository:
    """Handles all database operations for HistoricalOutcome."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(
        self, outcome: HistoricalOutcome,
    ) -> Result[HistoricalOutcome]:
        """Persist a single historical outcome record."""
        self._session.add(outcome)
        await self._session.flush()
        logger.debug("Outcome saved: %s", outcome.id)
        return Success(outcome)

    async def get_by_venue(
        self,
        venue_id: uuid.UUID,
        outcome_type: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Result[tuple[list[HistoricalOutcome], int]]:
        """Query outcomes for a venue with optional type filter and pagination."""
        base_query = select(HistoricalOutcome).where(
            HistoricalOutcome.venue_id == venue_id,
        )
        if outcome_type is not None:
            base_query = base_query.where(
                HistoricalOutcome.outcome_type == outcome_type,
            )

        count_stmt = select(func.count()).select_from(base_query.subquery())
        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar_one()

        paginated = (
            base_query
            .order_by(HistoricalOutcome.recorded_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self._session.execute(paginated)
        outcomes = list(result.scalars().all())
        return Success((outcomes, total))

    async def get_effectiveness_stats(
        self, venue_id: uuid.UUID,
    ) -> Result[dict]:
        """Compute intervention effectiveness statistics for a venue."""
        stmt = select(HistoricalOutcome).where(
            HistoricalOutcome.venue_id == venue_id,
        )
        result = await self._session.execute(stmt)
        outcomes = list(result.scalars().all())

        total = len(outcomes)
        evaluated = [o for o in outcomes if o.intervention_effective is not None]
        effective_count = sum(1 for o in evaluated if o.intervention_effective is True)

        score_changes = [
            o.risk_score_change
            for o in outcomes
            if o.risk_score_change is not None
        ]
        avg_score_change = (
            sum(score_changes) / len(score_changes) if score_changes else 0.0
        )

        durations = [
            o.duration_seconds
            for o in outcomes
            if o.duration_seconds is not None
        ]
        avg_duration = sum(durations) / len(durations) if durations else 0.0

        type_counts: dict[str, int] = {}
        type_effective: dict[str, int] = {}
        type_total: dict[str, int] = {}
        for o in outcomes:
            type_counts[o.outcome_type] = type_counts.get(o.outcome_type, 0) + 1
            if o.intervention_effective is not None:
                type_total[o.outcome_type] = type_total.get(o.outcome_type, 0) + 1
                if o.intervention_effective:
                    type_effective[o.outcome_type] = type_effective.get(o.outcome_type, 0) + 1

        effectiveness_by_type = {
            t: round(type_effective.get(t, 0) / type_total[t], 4)
            for t in type_total
            if type_total[t] > 0
        }

        return Success({
            "venue_id": str(venue_id),
            "total_outcomes": total,
            "evaluated_outcomes": len(evaluated),
            "effective_count": effective_count,
            "effectiveness_rate": (
                round(effective_count / len(evaluated), 4)
                if evaluated else 0.0
            ),
            "avg_risk_score_change": round(avg_score_change, 4),
            "avg_duration_seconds": round(avg_duration, 2),
            "outcome_type_counts": type_counts,
            "effectiveness_by_type": effectiveness_by_type,
        })
