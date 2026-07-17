"""Domain-specific exception hierarchy for the Digital Twin module."""

from __future__ import annotations


class DigitalTwinError(Exception):
    """Base exception for all digital twin errors."""

    def __init__(self, message: str, error_code: str, details: dict | None = None) -> None:
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class EntityNotFoundError(DigitalTwinError):
    """Raised when an entity cannot be found."""

    def __init__(self, entity_id: str = "entity", details: dict | None = None) -> None:
        super().__init__(
            message=f"Entity '{entity_id}' not found",
            error_code="ENTITY_NOT_FOUND",
            details=details,
        )


class ZoneNotFoundError(DigitalTwinError):
    """Raised when a zone cannot be found."""

    def __init__(self, zone_id: str = "zone", details: dict | None = None) -> None:
        super().__init__(
            message=f"Zone '{zone_id}' not found",
            error_code="ZONE_NOT_FOUND",
            details=details,
        )


class VenueNotFoundError(DigitalTwinError):
    """Raised when a venue cannot be found."""

    def __init__(self, venue_id: str = "venue", details: dict | None = None) -> None:
        super().__init__(
            message=f"Venue '{venue_id}' not found",
            error_code="VENUE_NOT_FOUND",
            details=details,
        )


class EdgeNotFoundError(DigitalTwinError):
    """Raised when an edge cannot be found."""

    def __init__(self, edge_id: str = "edge", details: dict | None = None) -> None:
        super().__init__(
            message=f"Edge '{edge_id}' not found",
            error_code="EDGE_NOT_FOUND",
            details=details,
        )


class InvalidGeometryError(DigitalTwinError):
    """Raised when spatial geometry is invalid."""

    def __init__(self, message: str = "Invalid geometry", details: dict | None = None) -> None:
        super().__init__(message=message, error_code="INVALID_GEOMETRY", details=details)


class InvalidCoordinateError(DigitalTwinError):
    """Raised when coordinates are out of valid range."""

    def __init__(self, details: dict | None = None) -> None:
        super().__init__(
            message="Coordinates out of valid range",
            error_code="INVALID_COORDINATES",
            details=details,
        )


class PathNotFoundError(DigitalTwinError):
    """Raised when no path exists between two entities."""

    def __init__(self, details: dict | None = None) -> None:
        super().__init__(
            message="No path found between the specified entities",
            error_code="PATH_NOT_FOUND",
            details=details,
        )


class CapacityExceededError(DigitalTwinError):
    """Raised when an entity's capacity would be exceeded."""

    def __init__(self, details: dict | None = None) -> None:
        super().__init__(
            message="Entity capacity exceeded",
            error_code="CAPACITY_EXCEEDED",
            details=details,
        )


class EntityValidationError(DigitalTwinError):
    """Raised when entity data fails validation."""

    def __init__(self, message: str = "Entity validation failed", details: dict | None = None) -> None:
        super().__init__(message=message, error_code="ENTITY_VALIDATION_FAILED", details=details)


class CyclicZoneError(DigitalTwinError):
    """Raised when a zone hierarchy would create a cycle."""

    def __init__(self, details: dict | None = None) -> None:
        super().__init__(
            message="Operation would create a cyclic zone hierarchy",
            error_code="CYCLIC_ZONE_HIERARCHY",
            details=details,
        )
