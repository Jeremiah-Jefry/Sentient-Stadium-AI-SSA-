"""Domain-specific exception hierarchy for the Event Streaming module."""

from __future__ import annotations


class EventStreamingError(Exception):
    """Base exception for all event streaming errors."""

    def __init__(self, message: str, error_code: str, details: dict | None = None) -> None:
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class EventValidationError(EventStreamingError):
    """Raised when an event fails schema or field validation."""

    def __init__(
        self,
        message: str = "Event validation failed",
        details: dict | None = None,
    ) -> None:
        super().__init__(message=message, error_code="EVENT_VALIDATION_FAILED", details=details)


class EventDuplicateError(EventStreamingError):
    """Raised when a duplicate event ID is detected during ingestion."""

    def __init__(self, event_id: str = "", details: dict | None = None) -> None:
        super().__init__(
            message=f"Duplicate event: {event_id}",
            error_code="EVENT_DUPLICATE",
            details=details,
        )


class EventExpiredError(EventStreamingError):
    """Raised when an event has exceeded its TTL before processing."""

    def __init__(self, event_id: str = "", details: dict | None = None) -> None:
        super().__init__(
            message=f"Event expired: {event_id}",
            error_code="EVENT_EXPIRED",
            details=details,
        )


class PipelineStageError(EventStreamingError):
    """Raised when a processing pipeline stage fails."""

    def __init__(
        self,
        stage: str = "",
        message: str = "Pipeline stage failed",
        details: dict | None = None,
    ) -> None:
        super().__init__(
            message=f"Stage '{stage}': {message}",
            error_code="PIPELINE_STAGE_FAILED",
            details=details,
        )


class ConsumerError(EventStreamingError):
    """Raised when a consumer fails to process an event."""

    def __init__(
        self,
        consumer_id: str = "",
        message: str = "Consumer failed",
        details: dict | None = None,
    ) -> None:
        super().__init__(
            message=f"Consumer '{consumer_id}': {message}",
            error_code="CONSUMER_FAILED",
            details=details,
        )


class SensorNotFoundError(EventStreamingError):
    """Raised when a sensor cannot be found in the registry."""

    def __init__(self, sensor_id: str = "sensor", details: dict | None = None) -> None:
        super().__init__(
            message=f"Sensor '{sensor_id}' not found",
            error_code="SENSOR_NOT_FOUND",
            details=details,
        )


class SensorInactiveError(EventStreamingError):
    """Raised when attempting to process readings from an inactive sensor."""

    def __init__(self, sensor_id: str = "sensor", details: dict | None = None) -> None:
        super().__init__(
            message=f"Sensor '{sensor_id}' is inactive",
            error_code="SENSOR_INACTIVE",
            details=details,
        )


class ReplayError(EventStreamingError):
    """Raised when a replay operation fails."""

    def __init__(
        self,
        message: str = "Replay operation failed",
        details: dict | None = None,
    ) -> None:
        super().__init__(message=message, error_code="REPLAY_FAILED", details=details)


class FusionError(EventStreamingError):
    """Raised when sensor fusion computation fails."""

    def __init__(
        self,
        message: str = "Fusion computation failed",
        details: dict | None = None,
    ) -> None:
        super().__init__(message=message, error_code="FUSION_FAILED", details=details)


class CacheError(EventStreamingError):
    """Raised when cache operations fail."""

    def __init__(
        self,
        message: str = "Cache operation failed",
        details: dict | None = None,
    ) -> None:
        super().__init__(message=message, error_code="CACHE_FAILED", details=details)
