"""Repository for AgentHealthRecord records."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.orchestration.models.database import AgentHealthRecord
from app.shared.result import Failure, Result, Success

logger = logging.getLogger(__name__)


class AgentHealthRepository:
    """Handles all database operations for agent health telemetry."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, record: AgentHealthRecord) -> Result[AgentHealthRecord]:
        self._session.add(record)
        await self._session.flush()
        logger.debug("AgentHealthRecord saved: %s", record.id)
        return Success(record)

    async def get_by_agent_id(
        self, agent_id: uuid.UUID,
    ) -> Result[AgentHealthRecord | None]:
        stmt = (
            select(AgentHealthRecord)
            .where(AgentHealthRecord.agent_id == agent_id)
            .order_by(AgentHealthRecord.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return Success(result.scalar_one_or_none())

    async def get_all_agents(self) -> Result[list[AgentHealthRecord]]:
        """Return the latest health record per agent_id."""
        subquery = (
            select(
                AgentHealthRecord.agent_id,
                func.max(AgentHealthRecord.created_at).label("latest"),
            )
            .group_by(AgentHealthRecord.agent_id)
            .subquery()
        )
        stmt = (
            select(AgentHealthRecord)
            .join(
                subquery,
                (AgentHealthRecord.agent_id == subquery.c.agent_id)
                & (AgentHealthRecord.created_at == subquery.c.latest),
            )
            .order_by(AgentHealthRecord.agent_name.asc())
        )
        result = await self._session.execute(stmt)
        return Success(list(result.scalars().all()))

    async def update_health(
        self,
        agent_id: uuid.UUID,
        status: str,
        health_score: float,
        current_load: int,
    ) -> Result[AgentHealthRecord]:
        stmt = (
            select(AgentHealthRecord)
            .where(AgentHealthRecord.agent_id == agent_id)
            .order_by(AgentHealthRecord.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        record = result.scalar_one_or_none()

        if record is None:
            return Failure(
                error_code="AGENT_HEALTH_NOT_FOUND",
                message=f"No health record found for agent {agent_id}",
            )

        record.status = status
        record.health_score = health_score
        record.current_load = current_load
        await self._session.flush()
        logger.debug("Agent %s health updated: score=%.2f", agent_id, health_score)
        return Success(record)

    async def get_agents_by_status(
        self, status: str,
    ) -> Result[list[AgentHealthRecord]]:
        subquery = (
            select(
                AgentHealthRecord.agent_id,
                func.max(AgentHealthRecord.created_at).label("latest"),
            )
            .where(AgentHealthRecord.status == status)
            .group_by(AgentHealthRecord.agent_id)
            .subquery()
        )
        stmt = (
            select(AgentHealthRecord)
            .join(
                subquery,
                (AgentHealthRecord.agent_id == subquery.c.agent_id)
                & (AgentHealthRecord.created_at == subquery.c.latest),
            )
            .order_by(AgentHealthRecord.health_score.asc())
        )
        result = await self._session.execute(stmt)
        return Success(list(result.scalars().all()))

    async def get_unhealthy_agents(
        self, threshold: float = 0.5,
    ) -> Result[list[AgentHealthRecord]]:
        """Return agents whose latest health_score falls below the threshold."""
        subquery = (
            select(
                AgentHealthRecord.agent_id,
                func.max(AgentHealthRecord.created_at).label("latest"),
            )
            .group_by(AgentHealthRecord.agent_id)
            .subquery()
        )
        stmt = (
            select(AgentHealthRecord)
            .join(
                subquery,
                (AgentHealthRecord.agent_id == subquery.c.agent_id)
                & (AgentHealthRecord.created_at == subquery.c.latest),
            )
            .where(AgentHealthRecord.health_score < threshold)
            .order_by(AgentHealthRecord.health_score.asc())
        )
        result = await self._session.execute(stmt)
        return Success(list(result.scalars().all()))
