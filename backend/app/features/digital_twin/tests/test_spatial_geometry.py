"""Unit tests for spatial geometry validation utilities."""

import pytest

from app.features.digital_twin.exceptions import InvalidCoordinateError, InvalidGeometryError
from app.features.digital_twin.spatial.geometry import (
    compute_bbox_from_points,
    point_in_bbox,
    validate_bounding_box,
    validate_coordinates,
    validate_polygon,
)


class TestValidateCoordinates:
    def test_valid_coordinates(self) -> None:
        validate_coordinates(40.0, -74.0)

    def test_equator_prime_meridian(self) -> None:
        validate_coordinates(0.0, 0.0)

    def test_boundary_values(self) -> None:
        validate_coordinates(90.0, 180.0)
        validate_coordinates(-90.0, -180.0)

    def test_latitude_too_high(self) -> None:
        with pytest.raises(InvalidCoordinateError):
            validate_coordinates(91.0, 0.0)

    def test_latitude_too_low(self) -> None:
        with pytest.raises(InvalidCoordinateError):
            validate_coordinates(-91.0, 0.0)

    def test_longitude_too_high(self) -> None:
        with pytest.raises(InvalidCoordinateError):
            validate_coordinates(0.0, 181.0)

    def test_longitude_too_low(self) -> None:
        with pytest.raises(InvalidCoordinateError):
            validate_coordinates(0.0, -181.0)


class TestValidatePolygon:
    def test_valid_polygon(self) -> None:
        polygon = [[
            [-74.0, 40.0],
            [-73.9, 40.0],
            [-73.9, 40.1],
            [-74.0, 40.1],
            [-74.0, 40.0],
        ]]
        validate_polygon(polygon)

    def test_too_few_points(self) -> None:
        polygon = [[
            [-74.0, 40.0],
            [-73.9, 40.0],
            [-74.0, 40.0],
        ]]
        with pytest.raises(InvalidGeometryError):
            validate_polygon(polygon)

    def test_unclosed_ring(self) -> None:
        polygon = [[
            [-74.0, 40.0],
            [-73.9, 40.0],
            [-73.9, 40.1],
            [-74.0, 40.1],
        ]]
        with pytest.raises(InvalidGeometryError):
            validate_polygon(polygon)

    def test_empty_polygon(self) -> None:
        with pytest.raises(InvalidGeometryError):
            validate_polygon([])

    def test_invalid_coordinates_in_ring(self) -> None:
        polygon = [[
            [-74.0, 40.0],
            [200.0, 40.0],
            [200.0, 40.1],
            [-74.0, 40.1],
            [-74.0, 40.0],
        ]]
        with pytest.raises(InvalidCoordinateError):
            validate_polygon(polygon)


class TestBoundingBox:
    def test_valid_bbox(self) -> None:
        validate_bounding_box(40.0, 40.1, -74.0, -73.9)

    def test_lat_min_greater_than_max(self) -> None:
        with pytest.raises(InvalidGeometryError):
            validate_bounding_box(40.1, 40.0, -74.0, -73.9)

    def test_lon_min_greater_than_max(self) -> None:
        with pytest.raises(InvalidGeometryError):
            validate_bounding_box(40.0, 40.1, -73.9, -74.0)


class TestPointInBbox:
    def test_inside(self) -> None:
        assert point_in_bbox(40.05, -73.95, 40.0, 40.1, -74.0, -73.9) is True

    def test_outside(self) -> None:
        assert point_in_bbox(41.0, -73.95, 40.0, 40.1, -74.0, -73.9) is False

    def test_on_boundary(self) -> None:
        assert point_in_bbox(40.0, -74.0, 40.0, 40.1, -74.0, -73.9) is True


class TestComputeBbox:
    def test_normal(self) -> None:
        points = [(40.0, -74.0), (40.1, -73.9), (40.05, -73.95)]
        result = compute_bbox_from_points(points)
        assert result["lat_min"] == 40.0
        assert result["lat_max"] == 40.1
        assert result["lon_min"] == -74.0
        assert result["lon_max"] == -73.9

    def test_empty_points(self) -> None:
        result = compute_bbox_from_points([])
        assert result["lat_min"] == 0

    def test_single_point(self) -> None:
        result = compute_bbox_from_points([(40.0, -74.0)])
        assert result["lat_min"] == 40.0
        assert result["lat_max"] == 40.0
