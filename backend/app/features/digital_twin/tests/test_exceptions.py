"""Unit tests for digital twin exception hierarchy."""

from app.features.digital_twin.exceptions import (
    CapacityExceededError,
    CyclicZoneError,
    DigitalTwinError,
    EdgeNotFoundError,
    EntityNotFoundError,
    EntityValidationError,
    InvalidCoordinateError,
    InvalidGeometryError,
    PathNotFoundError,
    VenueNotFoundError,
    ZoneNotFoundError,
)


class TestExceptionHierarchy:
    def test_base_exception(self) -> None:
        exc = DigitalTwinError(message="test", error_code="TEST")
        assert exc.message == "test"
        assert exc.error_code == "TEST"
        assert exc.details == {}
        assert isinstance(exc, Exception)

    def test_entity_not_found(self) -> None:
        exc = EntityNotFoundError("abc-123")
        assert "abc-123" in exc.message
        assert exc.error_code == "ENTITY_NOT_FOUND"

    def test_zone_not_found(self) -> None:
        exc = ZoneNotFoundError("zone-456")
        assert "zone-456" in exc.message
        assert exc.error_code == "ZONE_NOT_FOUND"

    def test_venue_not_found(self) -> None:
        exc = VenueNotFoundError("venue-789")
        assert exc.error_code == "VENUE_NOT_FOUND"

    def test_edge_not_found(self) -> None:
        exc = EdgeNotFoundError()
        assert exc.error_code == "EDGE_NOT_FOUND"

    def test_invalid_geometry(self) -> None:
        exc = InvalidGeometryError()
        assert exc.error_code == "INVALID_GEOMETRY"

    def test_invalid_coordinate(self) -> None:
        exc = InvalidCoordinateError(details={"lat": 91.0})
        assert exc.error_code == "INVALID_COORDINATES"
        assert exc.details["lat"] == 91.0

    def test_path_not_found(self) -> None:
        exc = PathNotFoundError()
        assert exc.error_code == "PATH_NOT_FOUND"

    def test_capacity_exceeded(self) -> None:
        exc = CapacityExceededError()
        assert exc.error_code == "CAPACITY_EXCEEDED"

    def test_entity_validation_error(self) -> None:
        exc = EntityValidationError(message="Bad entity")
        assert exc.message == "Bad entity"
        assert exc.error_code == "ENTITY_VALIDATION_FAILED"

    def test_cyclic_zone(self) -> None:
        exc = CyclicZoneError()
        assert exc.error_code == "CYCLIC_ZONE_HIERARCHY"

    def test_all_inherit_from_base(self) -> None:
        exceptions = [
            EntityNotFoundError(), ZoneNotFoundError(), VenueNotFoundError(),
            EdgeNotFoundError(), InvalidGeometryError(), InvalidCoordinateError(),
            PathNotFoundError(), CapacityExceededError(), EntityValidationError(),
            CyclicZoneError(),
        ]
        for exc in exceptions:
            assert isinstance(exc, DigitalTwinError)
            assert isinstance(exc, Exception)
