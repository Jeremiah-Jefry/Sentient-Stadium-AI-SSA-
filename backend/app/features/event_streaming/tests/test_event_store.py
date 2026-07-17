"""Tests for the event store repository."""

from __future__ import annotations

import uuid

from app.features.event_streaming.models.event import StoredEvent
from app.features.event_streaming.models.event_type import (
    EventCategory,
    EventPriority,
    EventSeverity,
    ProcessingStatus,
)


def _stored_event(**overrides: object) -> StoredEvent:
    defaults = {
        "event_id": f"evt-{uuid.uuid4().hex[:8]}",
        "event_type": "crowd_density_update",
        "category": EventCategory.CROWD,
        "priority": EventPriority.NORMAL,
        "severity": EventSeverity.INFO,
        "source": "test-sensor",
        "producer": "test",
        "version": 1,
        "payload": {"crowd_density": 5000},
        "captured_at": "2026-07-15T20:00:00Z",
        "processing_status": ProcessingStatus.RECEIVED,
        "retry_count": 0,
        "max_retries": 3,
    }
    defaults.update(overrides)
    return StoredEvent(**defaults)  # type: ignore[arg-type]


class TestStoredEventModel:
    def test_event_creation(self) -> None:
        event = _stored_event()
        assert event.event_id
        assert event.category == EventCategory.CROWD
        assert event.processing_status == ProcessingStatus.RECEIVED

    def test_event_with_entity(self) -> None:
        event = _stored_event(
            entity_id=uuid.uuid4(),
            venue_id=uuid.uuid4(),
            zone_id=uuid.uuid4(),
        )
        assert event.entity_id is not None
        assert event.venue_id is not None

    def test_event_with_metadata(self) -> None:
        event = _stored_event(
            metadata_json={"source": "test", "version": 2},
        )
        assert event.metadata_json is not None

    def test_event_defaults(self) -> None:
        event = _stored_event()
        assert event.retry_count == 0
        assert event.max_retries == 3
        assert event.version == 1


class TestEventCategory:
    def test_all_categories_exist(self) -> None:
        categories = [
            "crowd", "security", "medical", "transport", "weather",
            "infrastructure", "operations", "emergency", "sensor", "system",
        ]
        for cat in categories:
            assert EventCategory(cat).value == cat


class TestProcessingStatus:
    def test_lifecycle_statuses(self) -> None:
        assert ProcessingStatus.RECEIVED.value == "received"
        assert ProcessingStatus.PROCESSED.value == "processed"
        assert ProcessingStatus.FAILED.value == "failed"
        assert ProcessingStatus.DEAD_LETTERED.value == "dead_lettered"
