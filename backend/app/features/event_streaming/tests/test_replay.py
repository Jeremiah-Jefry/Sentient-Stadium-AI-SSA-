"""Tests for the replay service."""

from __future__ import annotations

import pytest

from app.features.event_streaming.engine.event_bus import EventBus
from app.features.event_streaming.engine.pipeline import StreamingPipeline
from app.features.event_streaming.services.replay_service import ReplayService


class TestReplayService:
    @pytest.mark.asyncio
    async def test_cancel_nonexistent_replay(self) -> None:
        service = ReplayService(
            event_store=None,  # type: ignore[arg-type]
            pipeline=StreamingPipeline(event_bus=EventBus()),
        )
        result = service.cancel_replay("nonexistent")
        assert result is False

    def test_active_replays_empty(self) -> None:
        service = ReplayService(
            event_store=None,  # type: ignore[arg-type]
            pipeline=StreamingPipeline(event_bus=EventBus()),
        )
        assert service.active_replays == []

    def test_stats_initial(self) -> None:
        service = ReplayService(
            event_store=None,  # type: ignore[arg-type]
            pipeline=StreamingPipeline(event_bus=EventBus()),
        )
        stats = service.stats
        assert stats["total_replayed"] == 0
        assert stats["active_count"] == 0
