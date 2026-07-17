"""Replay engine — replays historical events through the processing pipeline."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid

from app.features.event_streaming.dto.event_requests import ReplayRequest
from app.features.event_streaming.engine.pipeline import PipelineContext, StreamingPipeline
from app.features.event_streaming.exceptions import ReplayError
from app.features.event_streaming.repositories.event_store_repository import EventStoreRepository
from app.shared.result import Result, Success

logger = logging.getLogger(__name__)

DEFAULT_REPLAY_BATCH_SIZE = 500


class ReplayService:
    """Replays historical events through the processing pipeline.

    Supports configurable speed multipliers and selective replay by
    venue, entity, category, and time range.
    """

    def __init__(
        self,
        event_store: EventStoreRepository,
        pipeline: StreamingPipeline,
    ) -> None:
        self._event_store = event_store
        self._pipeline = pipeline
        self._active_replays: dict[str, bool] = {}
        self._total_replayed = 0

    async def replay(self, req: ReplayRequest) -> Result[dict]:
        """Execute a replay of historical events with cursor-based pagination."""
        replay_id = f"replay_{int(time.time() * 1000)}"
        self._active_replays[replay_id] = True

        venue_uuid = uuid.UUID(req.venue_id) if req.venue_id else None
        total_replayed = 0
        total_failed = 0
        cursor: str | None = req.from_timestamp

        try:
            while cursor and self._active_replays.get(replay_id, False):
                batch_result = await self._event_store.get_time_range(
                    from_timestamp=cursor,
                    to_timestamp=req.to_timestamp,
                    venue_id=venue_uuid,
                    category=req.category.value if req.category else None,
                    batch_size=DEFAULT_REPLAY_BATCH_SIZE,
                )

                if not isinstance(batch_result, Success):
                    raise ReplayError(message="Failed to fetch events for replay")

                events = batch_result.value
                if not events:
                    break

                contexts = [
                    PipelineContext(
                        event_id=e.event_id,
                        event_type=e.event_type,
                        category=e.category,
                        payload=e.payload,
                        venue_id=str(e.venue_id) if e.venue_id else None,
                        entity_id=str(e.entity_id) if e.entity_id else None,
                        zone_id=str(e.zone_id) if e.zone_id else None,
                        priority=e.priority,
                        severity=e.severity,
                        captured_at=e.captured_at,
                        producer=e.producer,
                        metadata={"replay_id": replay_id, "is_replay": True},
                    )
                    for e in events
                ]

                results = await self._pipeline.process_batch(contexts)
                succeeded = sum(1 for r in results if r.status.value == "processed")
                total_replayed += succeeded
                total_failed += len(results) - succeeded

                # Advance cursor past the last event in this batch
                last_captured = events[-1].captured_at
                if last_captured == cursor:
                    break
                cursor = last_captured

                delay = DEFAULT_REPLAY_BATCH_SIZE / (req.speed_multiplier * 1000)
                if delay > 0:
                    await asyncio.sleep(min(delay, 1.0))

        except Exception as exc:
            logger.exception("Replay %s failed", replay_id)
            self._active_replays.pop(replay_id, None)
            raise ReplayError(message=f"Replay failed: {exc}") from exc

        self._active_replays.pop(replay_id, None)
        self._total_replayed += total_replayed

        return Success({
            "replay_id": replay_id,
            "total_replayed": total_replayed,
            "total_failed": total_failed,
            "status": "completed",
        })

    def cancel_replay(self, replay_id: str) -> bool:
        """Cancel an active replay."""
        if replay_id in self._active_replays:
            self._active_replays[replay_id] = False
            return True
        return False

    @property
    def active_replays(self) -> list[str]:
        return [rid for rid, active in self._active_replays.items() if active]

    @property
    def stats(self) -> dict:
        return {
            "total_replayed": self._total_replayed,
            "active_count": len(self.active_replays),
        }
