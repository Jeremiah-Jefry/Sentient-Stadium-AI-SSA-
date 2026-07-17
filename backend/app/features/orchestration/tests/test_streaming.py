"""Tests for StreamingManager — stream creation, event pushing, completion, and session cleanup."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from app.features.orchestration.dto.response import StreamingChunk
from app.features.orchestration.models.enums import StreamingEventType
from app.features.orchestration.streaming.streaming_manager import StreamingManager


@pytest.fixture
def manager() -> StreamingManager:
    return StreamingManager()


def _make_chunk(
    event_type: StreamingEventType = StreamingEventType.PROGRESS,
    data: dict | None = None,
    execution_id: UUID | None = None,
    step_id: UUID | None = None,
) -> StreamingChunk:
    return StreamingChunk(
        event_type=event_type,
        data=data or {"message": "test"},
        timestamp=datetime.now(UTC),
        execution_id=execution_id or uuid4(),
        step_id=step_id,
    )


class TestStreamingManager:

    @pytest.mark.asyncio
    async def test_create_stream(self, manager: StreamingManager) -> None:
        exec_id = uuid4()
        session = await manager.create_stream(exec_id)
        assert session.execution_id == exec_id
        assert session.status == "active"
        assert len(session.events) == 0

    @pytest.mark.asyncio
    async def test_create_stream_registered(self, manager: StreamingManager) -> None:
        session = await manager.create_stream(uuid4())
        retrieved = manager.get_session(session.session_id)
        assert retrieved is not None
        assert retrieved.session_id == session.session_id

    @pytest.mark.asyncio
    async def test_push_event(self, manager: StreamingManager) -> None:
        session = await manager.create_stream(uuid4())
        chunk = _make_chunk(
            event_type=StreamingEventType.AGENT_STATUS,
            data={"agent": "Crowd Agent", "status": "running"},
            execution_id=session.execution_id,
        )
        await manager.push_event(session.session_id, chunk)
        updated = manager.get_session(session.session_id)
        assert len(updated.events) == 1
        assert updated.events[0].event_type == StreamingEventType.AGENT_STATUS

    @pytest.mark.asyncio
    async def test_push_event_unknown_session(self, manager: StreamingManager) -> None:
        chunk = _make_chunk()
        await manager.push_event(uuid4(), chunk)
        assert True

    @pytest.mark.asyncio
    async def test_push_event_completed_session(self, manager: StreamingManager) -> None:
        session = await manager.create_stream(uuid4())
        await manager.complete_stream(session.session_id)
        chunk = _make_chunk(execution_id=session.execution_id)
        await manager.push_event(session.session_id, chunk)
        updated = manager.get_session(session.session_id)
        assert len(updated.events) == 0

    @pytest.mark.asyncio
    async def test_complete_stream(self, manager: StreamingManager) -> None:
        session = await manager.create_stream(uuid4())
        await manager.complete_stream(session.session_id)
        updated = manager.get_session(session.session_id)
        assert updated.status == "completed"

    @pytest.mark.asyncio
    async def test_cancel_stream(self, manager: StreamingManager) -> None:
        session = await manager.create_stream(uuid4())
        await manager.cancel_stream(session.session_id)
        updated = manager.get_session(session.session_id)
        assert updated.status == "cancelled"

    @pytest.mark.asyncio
    async def test_get_next_returns_event(self, manager: StreamingManager) -> None:
        session = await manager.create_stream(uuid4())
        chunk = _make_chunk(execution_id=session.execution_id)
        await manager.push_event(session.session_id, chunk)
        latest = await manager.get_next(session.session_id, timeout_seconds=1.0)
        assert latest is not None
        assert latest.event_type == StreamingEventType.PROGRESS

    @pytest.mark.asyncio
    async def test_get_next_timeout(self, manager: StreamingManager) -> None:
        session = await manager.create_stream(uuid4())
        latest = await manager.get_next(session.session_id, timeout_seconds=0.05)
        assert latest is None

    @pytest.mark.asyncio
    async def test_get_active_sessions(self, manager: StreamingManager) -> None:
        s1 = await manager.create_stream(uuid4())
        s2 = await manager.create_stream(uuid4())
        await manager.complete_stream(s1.session_id)
        active = manager.get_active_sessions()
        assert len(active) == 1
        assert active[0].session_id == s2.session_id

    @pytest.mark.asyncio
    async def test_cleanup_expired(self, manager: StreamingManager) -> None:
        s1 = await manager.create_stream(uuid4())
        await manager.complete_stream(s1.session_id)
        session = manager.get_session(s1.session_id)
        session.last_event_at = datetime.now(UTC) - timedelta(seconds=400)

        s2 = await manager.create_stream(uuid4())
        await manager.complete_stream(s2.session_id)

        removed = await manager.cleanup_expired(max_age_seconds=300.0)
        assert removed == 1
        assert manager.get_session(s1.session_id) is None
        assert manager.get_session(s2.session_id) is not None

    @pytest.mark.asyncio
    async def test_cleanup_active_not_removed(self, manager: StreamingManager) -> None:
        await manager.create_stream(uuid4())
        removed = await manager.cleanup_expired(max_age_seconds=0.0)
        assert removed == 0

    @pytest.mark.asyncio
    async def test_multiple_events(self, manager: StreamingManager) -> None:
        session = await manager.create_stream(uuid4())
        for i in range(5):
            chunk = _make_chunk(
                event_type=StreamingEventType.PARTIAL_RESULT,
                data={"step": i},
                execution_id=session.execution_id,
            )
            await manager.push_event(session.session_id, chunk)
        updated = manager.get_session(session.session_id)
        assert len(updated.events) == 5
