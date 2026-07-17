from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.features.orchestration.dto.response import StreamingChunk

logging = logging.getLogger(__name__)


@dataclass
class StreamingSession:
    session_id: UUID
    execution_id: UUID
    status: str
    events: list[StreamingChunk] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_event_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    _event_ready: asyncio.Event = field(default_factory=asyncio.Event, repr=False)


class StreamingManager:
    def __init__(self) -> None:
        self._sessions: dict[UUID, StreamingSession] = {}

    async def create_stream(self, execution_id: UUID) -> StreamingSession:
        session_id = uuid4()
        session = StreamingSession(
            session_id=session_id,
            execution_id=execution_id,
            status="active",
        )
        self._sessions[session_id] = session
        logging.info("Created streaming session %s for execution %s", session_id, execution_id)
        return session

    async def push_event(self, session_id: UUID, event: StreamingChunk) -> None:
        session = self._sessions.get(session_id)
        if session is None:
            logging.warning("push_event called for unknown session %s", session_id)
            return

        if session.status != "active":
            logging.warning("push_event called on %s session %s", session.status, session_id)
            return

        session.events.append(event)
        session.last_event_at = datetime.now(UTC)
        session._event_ready.set()

    async def get_next(self, session_id: UUID, timeout_seconds: float = 30.0) -> StreamingChunk | None:
        session = self._sessions.get(session_id)
        if session is None:
            return None

        try:
            await asyncio.wait_for(session._event_ready.wait(), timeout=timeout_seconds)
        except TimeoutError:
            return None

        session._event_ready.clear()

        if not session.events:
            return None

        return session.events[-1]

    async def complete_stream(self, session_id: UUID) -> None:
        session = self._sessions.get(session_id)
        if session is None:
            logging.warning("complete_stream called for unknown session %s", session_id)
            return

        session.status = "completed"
        session._event_ready.set()
        logging.info("Completed streaming session %s", session_id)

    async def cancel_stream(self, session_id: UUID) -> None:
        session = self._sessions.get(session_id)
        if session is None:
            logging.warning("cancel_stream called for unknown session %s", session_id)
            return

        session.status = "cancelled"
        session._event_ready.set()
        logging.info("Cancelled streaming session %s", session_id)

    def get_session(self, session_id: UUID) -> StreamingSession | None:
        return self._sessions.get(session_id)

    def get_active_sessions(self) -> list[StreamingSession]:
        return [s for s in self._sessions.values() if s.status == "active"]

    async def cleanup_expired(self, max_age_seconds: float = 300.0) -> int:
        now = datetime.now(UTC)
        expired_ids: list[UUID] = []

        for session_id, session in self._sessions.items():
            if session.status == "active":
                continue

            elapsed = (now - session.last_event_at).total_seconds()
            if elapsed > max_age_seconds:
                expired_ids.append(session_id)

        for session_id in expired_ids:
            del self._sessions[session_id]

        if expired_ids:
            logging.info("Cleaned up %d expired streaming sessions", len(expired_ids))

        return len(expired_ids)
