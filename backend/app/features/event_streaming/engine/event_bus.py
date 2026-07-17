"""In-memory async event bus with backpressure and subscriber management."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

DEFAULT_MAX_SUBSCRIBERS = 100
DEFAULT_BACKPRESSURE_THRESHOLD = 10000
DEFAULT_BATCH_SIZE = 100
FLUSH_INTERVAL_SECONDS = 0.01


@dataclass(frozen=True, slots=True)
class EventBusEvent:
    """Event envelope for the in-memory event bus."""

    event_id: str
    category: str
    event_type: str
    payload: dict
    venue_id: str | None = None
    entity_id: str | None = None
    zone_id: str | None = None
    priority: str = "normal"
    severity: str = "info"
    captured_at: str = ""
    producer: str = ""


@dataclass(slots=True)
class Subscriber:
    """Registered event bus subscriber with callback and filter."""

    subscriber_id: str
    callback: Callable[[EventBusEvent], Awaitable[None]]
    categories: set[str] = field(default_factory=set)
    event_types: set[str] = field(default_factory=set)
    venue_ids: set[str] = field(default_factory=set)
    max_queue_size: int = DEFAULT_BACKPRESSURE_THRESHOLD
    _queue: asyncio.Queue[EventBusEvent] = field(default_factory=asyncio.Queue)
    _total_received: int = 0
    _total_dropped: int = 0


class EventBus:
    """In-memory async event bus with topic-based routing and backpressure.

    Supports:
    - Category-based and event-type-based routing
    - Per-venue subscription filtering
    - Per-subscriber backpressure with queue limits
    - Batch flushing for high-throughput processing
    - Dead letter handling on queue overflow
    """

    def __init__(
        self,
        max_subscribers: int = DEFAULT_MAX_SUBSCRIBERS,
        backpressure_threshold: int = DEFAULT_BACKPRESSURE_THRESHOLD,
    ) -> None:
        self._subscribers: dict[str, Subscriber] = {}
        self._category_subscribers: dict[str, set[str]] = defaultdict(set)
        self._type_subscribers: dict[str, set[str]] = defaultdict(set)
        self._venue_subscribers: dict[str, set[str]] = defaultdict(set)
        self._max_subscribers = max_subscribers
        self._backpressure_threshold = backpressure_threshold
        self._total_published = 0
        self._total_delivered = 0
        self._total_dead_lettered = 0
        self._start_time = time.monotonic()
        self._flush_task: asyncio.Task[None] | None = None
        self._running = False

    async def start(self) -> None:
        """Start the background flush loop."""
        if self._running:
            return
        self._running = True
        self._flush_task = asyncio.create_task(self._flush_loop())
        logger.info("EventBus started")

    async def stop(self) -> None:
        """Stop the background flush loop and drain queues."""
        self._running = False
        if self._flush_task and not self._flush_task.done():
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        logger.info("EventBus stopped")

    def subscribe(
        self,
        subscriber_id: str,
        callback: Callable[[EventBusEvent], Awaitable[None]],
        categories: set[str] | None = None,
        event_types: set[str] | None = None,
        venue_ids: set[str] | None = None,
        max_queue_size: int | None = None,
    ) -> bool:
        """Register a subscriber with optional filters. Returns False if at capacity."""
        if len(self._subscribers) >= self._max_subscribers:
            logger.warning("Subscriber limit reached: %d", self._max_subscribers)
            return False

        subscriber = Subscriber(
            subscriber_id=subscriber_id,
            callback=callback,
            categories=categories or set(),
            event_types=event_types or set(),
            venue_ids=venue_ids or set(),
            max_queue_size=max_queue_size or self._backpressure_threshold,
        )
        self._subscribers[subscriber_id] = subscriber

        for cat in subscriber.categories:
            self._category_subscribers[cat].add(subscriber_id)
        for evt_type in subscriber.event_types:
            self._type_subscribers[evt_type].add(subscriber_id)
        for vid in subscriber.venue_ids:
            self._venue_subscribers[vid].add(subscriber_id)

        logger.info("Subscriber registered: %s", subscriber_id)
        return True

    def unsubscribe(self, subscriber_id: str) -> bool:
        """Remove a subscriber. Returns False if not found."""
        subscriber = self._subscribers.pop(subscriber_id, None)
        if subscriber is None:
            return False

        for cat in subscriber.categories:
            self._category_subscribers[cat].discard(subscriber_id)
        for evt_type in subscriber.event_types:
            self._type_subscribers[evt_type].discard(subscriber_id)
        for vid in subscriber.venue_ids:
            self._venue_subscribers[vid].discard(subscriber_id)

        logger.info("Subscriber removed: %s", subscriber_id)
        return True

    async def publish(self, event: EventBusEvent) -> int:
        """Publish an event to all matching subscribers. Returns delivery count."""
        self._total_published += 1
        delivered = 0

        matching_ids = self._compute_matching_subscribers(event)

        for sub_id in matching_ids:
            subscriber = self._subscribers.get(sub_id)
            if subscriber is None:
                continue

            if subscriber._queue.full():
                subscriber._total_dropped += 1
                self._total_dead_lettered += 1
                logger.warning(
                    "Backpressure: dropping event %s for subscriber %s",
                    event.event_id, sub_id,
                )
                continue

            subscriber._queue.put_nowait(event)
            subscriber._total_received += 1
            delivered += 1

        self._total_delivered += delivered
        return delivered

    async def publish_batch(self, events: list[EventBusEvent]) -> int:
        """Publish multiple events. Returns total delivery count."""
        total = 0
        for event in events:
            total += await self.publish(event)
        return total

    def _compute_matching_subscribers(self, event: EventBusEvent) -> set[str]:
        """Compute the set of subscriber IDs that match an event's filters."""
        candidates: set[str] | None = None

        if event.category in self._category_subscribers:
            if candidates is None:
                candidates = set(self._category_subscribers[event.category])
            else:
                candidates |= self._category_subscribers[event.category]

        if event.event_type in self._type_subscribers:
            if candidates is None:
                candidates = set(self._type_subscribers[event.event_type])
            else:
                candidates |= self._type_subscribers[event.event_type]

        if event.venue_id and event.venue_id in self._venue_subscribers:
            if candidates is None:
                candidates = set(self._venue_subscribers[event.venue_id])
            else:
                candidates |= self._venue_subscribers[event.venue_id]

        if candidates is None:
            candidates = set(self._subscribers.keys())

        result: set[str] = set()
        for sub_id in candidates:
            subscriber = self._subscribers.get(sub_id)
            if subscriber is None:
                continue
            if self._matches_filters(subscriber, event):
                result.add(sub_id)
        return result

    @staticmethod
    def _matches_filters(subscriber: Subscriber, event: EventBusEvent) -> bool:
        """Check if an event passes a subscriber's filter criteria."""
        if subscriber.categories and event.category not in subscriber.categories:
            return False
        if subscriber.event_types and event.event_type not in subscriber.event_types:
            return False
        if subscriber.venue_ids and event.venue_id not in subscriber.venue_ids:
            return False
        return True

    async def _flush_loop(self) -> None:
        """Background loop that dispatches queued events to subscribers."""
        while self._running:
            try:
                for subscriber in list(self._subscribers.values()):
                    dispatched = 0
                    while not subscriber._queue.empty() and dispatched < DEFAULT_BATCH_SIZE:
                        event = subscriber._queue.get_nowait()
                        try:
                            await subscriber.callback(event)
                        except Exception:
                            logger.exception(
                                "Subscriber %s callback failed for event %s",
                                subscriber.subscriber_id, event.event_id,
                            )
                        dispatched += 1
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("EventBus flush loop error")
            await asyncio.sleep(FLUSH_INTERVAL_SECONDS)

    @property
    def stats(self) -> dict:
        """Current bus statistics for monitoring."""
        return {
            "total_published": self._total_published,
            "total_delivered": self._total_delivered,
            "total_dead_lettered": self._total_dead_lettered,
            "active_subscribers": len(self._subscribers),
            "uptime_seconds": time.monotonic() - self._start_time,
        }

    @staticmethod
    def create_event(
        event_type: str,
        category: str,
        payload: dict,
        **kwargs: object,
    ) -> EventBusEvent:
        """Factory method for creating bus events with auto-generated ID."""
        return EventBusEvent(
            event_id=str(uuid.uuid4()),
            category=category,
            event_type=event_type,
            payload=payload,
            **kwargs,
        )
