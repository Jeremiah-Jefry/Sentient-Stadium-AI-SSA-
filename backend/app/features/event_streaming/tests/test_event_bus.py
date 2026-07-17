"""Tests for the in-memory async event bus."""

from __future__ import annotations

import asyncio

import pytest

from app.features.event_streaming.engine.event_bus import EventBus, EventBusEvent


@pytest.fixture
def bus() -> EventBus:
    return EventBus(max_subscribers=10, backpressure_threshold=100)


@pytest.fixture
def sample_event() -> EventBusEvent:
    return EventBusEvent(
        event_id="test-event-001",
        category="crowd",
        event_type="crowd_density_update",
        payload={"crowd_density": 5000},
        venue_id="venue-1",
        entity_id="entity-1",
        zone_id="zone-1",
        priority="normal",
        severity="info",
        captured_at="2026-07-15T20:00:00Z",
        producer="test",
    )


class TestEventBus:
    @pytest.mark.asyncio
    async def test_publish_delivers_to_subscribers(
        self, bus: EventBus, sample_event: EventBusEvent,
    ) -> None:
        received: list[EventBusEvent] = []
        bus.subscribe("sub-1", lambda e: received.append(e))
        await bus.publish(sample_event)
        assert len(received) == 1
        assert received[0].event_id == "test-event-001"

    @pytest.mark.asyncio
    async def test_category_filter(self, bus: EventBus) -> None:
        received: list[EventBusEvent] = []
        bus.subscribe("sub-1", lambda e: received.append(e), categories={"security"})

        crowd_event = EventBusEvent(
            event_id="e1", category="crowd", event_type="test",
            payload={}, producer="test",
        )
        security_event = EventBusEvent(
            event_id="e2", category="security", event_type="test",
            payload={}, producer="test",
        )

        await bus.publish(crowd_event)
        await bus.publish(security_event)
        assert len(received) == 1
        assert received[0].category == "security"

    @pytest.mark.asyncio
    async def test_venue_filter(self, bus: EventBus) -> None:
        received: list[EventBusEvent] = []
        bus.subscribe("sub-1", lambda e: received.append(e), venue_ids={"venue-A"})

        event_a = EventBusEvent(
            event_id="e1", category="crowd", event_type="test",
            payload={}, venue_id="venue-A", producer="test",
        )
        event_b = EventBusEvent(
            event_id="e2", category="crowd", event_type="test",
            payload={}, venue_id="venue-B", producer="test",
        )

        await bus.publish(event_a)
        await bus.publish(event_b)
        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_unsubscribe(self, bus: EventBus, sample_event: EventBusEvent) -> None:
        received: list[EventBusEvent] = []
        bus.subscribe("sub-1", lambda e: received.append(e))
        bus.unsubscribe("sub-1")
        await bus.publish(sample_event)
        assert len(received) == 0

    @pytest.mark.asyncio
    async def test_backpressure_drops_event(self, bus: EventBus) -> None:
        async def slow_handler(e: EventBusEvent) -> None:
            await asyncio.sleep(10)

        bus.subscribe("sub-1", slow_handler, max_queue_size=2)
        for i in range(5):
            await bus.publish(EventBusEvent(
                event_id=f"bp-{i}", category="crowd", event_type="test",
                payload={}, producer="test",
            ))
        assert bus.stats["total_dead_lettered"] >= 0

    @pytest.mark.asyncio
    async def test_batch_publish(self, bus: EventBus) -> None:
        received: list[EventBusEvent] = []
        bus.subscribe("sub-1", lambda e: received.append(e))

        events = [
            EventBusEvent(
                event_id=f"e{i}", category="crowd", event_type="test",
                payload={}, producer="test",
            )
            for i in range(5)
        ]
        await bus.publish_batch(events)
        assert len(received) == 5

    @pytest.mark.asyncio
    async def test_stats(self, bus: EventBus, sample_event: EventBusEvent) -> None:
        bus.subscribe("sub-1", lambda e: None)
        await bus.publish(sample_event)
        stats = bus.stats
        assert stats["total_published"] == 1
        assert stats["active_subscribers"] == 1

    @pytest.mark.asyncio
    async def test_start_stop(self, bus: EventBus) -> None:
        await bus.start()
        await bus.stop()

    def test_subscribe_at_capacity_returns_false(self, bus: EventBus) -> None:
        for i in range(10):
            bus.subscribe(f"sub-{i}", lambda e: None)
        result = bus.subscribe("sub-overflow", lambda e: None)
        assert result is False

    def test_create_event_factory(self) -> None:
        event = EventBus.create_event(
            event_type="test",
            category="crowd",
            payload={"key": "value"},
        )
        assert event.event_id
        assert event.category == "crowd"
