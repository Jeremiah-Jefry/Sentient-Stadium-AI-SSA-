"""Base consumer — abstract class for downstream event consumers."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from app.features.event_streaming.engine.event_bus import EventBusEvent
from app.features.event_streaming.services.processing_service import ProcessingService

logger = logging.getLogger(__name__)


class BaseConsumer(ABC):
    """Abstract base class for all event consumers.

    Consumers receive events from the event bus and perform specific
    downstream actions (update digital twin, broadcast WebSocket, etc.).
    """

    def __init__(
        self,
        consumer_id: str,
        processing_service: ProcessingService,
    ) -> None:
        self._consumer_id = consumer_id
        self._processing_service = processing_service
        self._is_running = False
        self._events_processed = 0
        self._events_failed = 0

    @property
    def consumer_id(self) -> str:
        return self._consumer_id

    @abstractmethod
    async def handle_event(self, event: EventBusEvent) -> bool:
        """Handle a single event. Returns True if successful."""

    async def start(self) -> None:
        """Start the consumer."""
        self._is_running = True
        logger.info("Consumer '%s' started", self._consumer_id)

    async def stop(self) -> None:
        """Stop the consumer."""
        self._is_running = False
        logger.info("Consumer '%s' stopped", self._consumer_id)

    async def process_event(self, event: EventBusEvent) -> None:
        """Process an event with error handling and offset tracking."""
        import time

        start_ms = time.monotonic() * 1000
        success = False

        try:
            success = await self.handle_event(event)
        except Exception as exc:
            logger.exception(
                "Consumer '%s' failed on event %s",
                self._consumer_id, event.event_id,
            )

        processing_ms = (time.monotonic() * 1000) - start_ms
        await self._processing_service.update_consumer_offset(
            consumer_id=self._consumer_id,
            event_id=event.event_id,
            processing_ms=processing_ms,
            success=success,
        )

        if success:
            self._events_processed += 1
        else:
            self._events_failed += 1

    @property
    def stats(self) -> dict:
        return {
            "consumer_id": self._consumer_id,
            "is_running": self._is_running,
            "events_processed": self._events_processed,
            "events_failed": self._events_failed,
        }
