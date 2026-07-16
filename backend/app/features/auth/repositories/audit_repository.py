"""Audit repository - data access layer for append-only audit logging."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.auth.models.audit_log import AuditEventType, AuditLog
from app.shared.result import Result, Success


class AuditRepository:
    """Handles all database operations for audit logs.

    This repository enforces append-only semantics. There are no
    update or delete methods. Audit logs are immutable once written.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, audit_log: AuditLog) -> Result[AuditLog]:
        """Append a new audit log entry. Never fails silently."""
        self._session.add(audit_log)
        await self._session.flush()
        return Success(audit_log)

    async def get_by_id(self, log_id: uuid.UUID) -> Result[AuditLog | None]:
        """Fetch an audit log entry by ID."""
        stmt = select(AuditLog).where(AuditLog.id == log_id)
        result = await self._session.execute(stmt)
        return Success(result.scalar_one_or_none())

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        page: int = 1,
        page_size: int = 50,
        event_type: AuditEventType | None = None,
        since: datetime | None = None,
    ) -> Result[tuple[list[AuditLog], int]]:
        """List audit logs for a specific user with optional filtering."""
        base_query = select(AuditLog).where(AuditLog.user_id == user_id)

        if event_type:
            base_query = base_query.where(AuditLog.event_type == event_type)
        if since:
            base_query = base_query.where(AuditLog.created_at >= since)

        count_stmt = select(func.count()).select_from(base_query.subquery())
        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar_one()

        paginated = base_query.order_by(AuditLog.created_at.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size)

        result = await self._session.execute(paginated)
        logs = list(result.scalars().all())
        return Success((logs, total))

    async def list_by_event_type(
        self,
        event_type: AuditEventType,
        page: int = 1,
        page_size: int = 50,
        since: datetime | None = None,
    ) -> Result[tuple[list[AuditLog], int]]:
        """List all audit logs of a specific event type across all users."""
        base_query = select(AuditLog).where(AuditLog.event_type == event_type)

        if since:
            base_query = base_query.where(AuditLog.created_at >= since)

        count_stmt = select(func.count()).select_from(base_query.subquery())
        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar_one()

        paginated = base_query.order_by(AuditLog.created_at.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size)

        result = await self._session.execute(paginated)
        logs = list(result.scalars().all())
        return Success((logs, total))

    async def get_recent_failures(
        self,
        user_id: uuid.UUID,
        window_minutes: int = 30,
    ) -> Result[int]:
        """Count recent failed login attempts for a user within the time window."""
        since = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
        stmt = select(func.count()).where(
            AuditLog.user_id == user_id,
            AuditLog.event_type == AuditEventType.LOGIN_FAILURE,
            AuditLog.created_at >= since,
        )
        result = await self._session.execute(stmt)
        return Success(result.scalar_one())
