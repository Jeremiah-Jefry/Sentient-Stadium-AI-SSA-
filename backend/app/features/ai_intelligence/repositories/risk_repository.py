"""Risk repository — data access for risk history time-series records."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.ai_intelligence.models.risk_history import RiskHistory
from app.shared.result import Result, Success

logger = logging.getLogger(__name__)


class RiskRepository:
    """Handles all database operations for RiskHistory."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, risk: RiskHistory) -> Result[RiskHistory]:
        """Persist a single risk assessment."""
        self._session.add(risk)
        await self._session.flush()
        logger.debug("Risk assessment saved: %s", risk.id)
        return Success(risk)

    async def get_latest_by_venue(
        self,
        venue_id: uuid.UUID,
        zone_id: uuid.UUID | None = None,
    ) -> Result[RiskHistory | None]:
        """Fetch the most recent risk assessment for a venue or zone."""
        stmt = (
            select(RiskHistory)
            .where(RiskHistory.venue_id == venue_id)
            .order_by(RiskHistory.assessed_at.desc())
            .limit(1)
        )
        if zone_id is not None:
            stmt = stmt.where(RiskHistory.zone_id == zone_id)

        result = await self._session.execute(stmt)
        return Success(result.scalar_one_or_none())

    async def get_history(
        self,
        venue_id: uuid.UUID,
        zone_id: uuid.UUID | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Result[tuple[list[RiskHistory], int]]:
        """Query risk history with time range, pagination, and zone filter."""
        base_query = select(RiskHistory).where(RiskHistory.venue_id == venue_id)

        if zone_id is not None:
            base_query = base_query.where(RiskHistory.zone_id == zone_id)
        if since is not None:
            base_query = base_query.where(RiskHistory.assessed_at >= since)
        if until is not None:
            base_query = base_query.where(RiskHistory.assessed_at <= until)

        count_stmt = select(func.count()).select_from(base_query.subquery())
        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar_one()

        paginated = (
            base_query
            .order_by(RiskHistory.assessed_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self._session.execute(paginated)
        records = list(result.scalars().all())
        return Success((records, total))

    async def get_trend(
        self,
        venue_id: uuid.UUID,
        zone_id: uuid.UUID | None = None,
        lookback_minutes: int = 60,
    ) -> Result[dict]:
        """Compute risk trend over a recent time window."""
        cutoff = datetime.now(timezone.utc)
        from datetime import timedelta

        cutoff = cutoff - timedelta(minutes=lookback_minutes)

        stmt = (
            select(RiskHistory)
            .where(
                RiskHistory.venue_id == venue_id,
                RiskHistory.assessed_at >= cutoff,
            )
            .order_by(RiskHistory.assessed_at.asc())
        )
        if zone_id is not None:
            stmt = stmt.where(RiskHistory.zone_id == zone_id)

        result = await self._session.execute(stmt)
        records = list(result.scalars().all())

        if not records:
            return Success({
                "venue_id": str(venue_id),
                "zone_id": str(zone_id) if zone_id else None,
                "lookback_minutes": lookback_minutes,
                "data_points": 0,
                "current_risk_score": 0.0,
                "min_risk_score": 0.0,
                "max_risk_score": 0.0,
                "avg_risk_score": 0.0,
                "trend_direction": "stable",
                "risk_level_counts": {},
            })

        scores = [r.risk_score for r in records]
        risk_level_counts: dict[str, int] = {}
        for r in records:
            risk_level_counts[r.risk_level] = risk_level_counts.get(r.risk_level, 0) + 1

        first_half = scores[: len(scores) // 2] if len(scores) > 1 else scores
        second_half = scores[len(scores) // 2 :] if len(scores) > 1 else scores
        first_avg = sum(first_half) / len(first_half) if first_half else 0.0
        second_avg = sum(second_half) / len(second_half) if second_half else 0.0

        if second_avg > first_avg * 1.05:
            trend = "rising"
        elif second_avg < first_avg * 0.95:
            trend = "falling"
        else:
            trend = "stable"

        return Success({
            "venue_id": str(venue_id),
            "zone_id": str(zone_id) if zone_id else None,
            "lookback_minutes": lookback_minutes,
            "data_points": len(records),
            "current_risk_score": scores[-1],
            "min_risk_score": round(min(scores), 4),
            "max_risk_score": round(max(scores), 4),
            "avg_risk_score": round(sum(scores) / len(scores), 4),
            "trend_direction": trend,
            "risk_level_counts": risk_level_counts,
        })
