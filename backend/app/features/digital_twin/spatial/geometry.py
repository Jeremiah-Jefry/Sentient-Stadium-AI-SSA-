"""Coordinate and geometry validation utilities."""

from __future__ import annotations

import re
from typing import Any

from app.features.digital_twin.exceptions import InvalidCoordinateError, InvalidGeometryError

# WGS84 coordinate bounds
LAT_MIN = -90.0
LAT_MAX = 90.0
LON_MIN = -180.0
LON_MAX = 180.0

# Haversine radius in meters
EARTH_RADIUS_METERS = 6_371_000


def validate_coordinates(lat: float, lon: float) -> None:
    """Validate that coordinates are within WGS84 bounds."""
    if not (LAT_MIN <= lat <= LAT_MAX):
        raise InvalidCoordinateError(details={"latitude": lat, "valid_range": [LAT_MIN, LAT_MAX]})
    if not (LON_MIN <= lon <= LON_MAX):
        raise InvalidCoordinateError(details={"longitude": lon, "valid_range": [LON_MIN, LON_MAX]})


def validate_polygon(polygon: list[list[float]]) -> None:
    """Validate polygon format: list of [lon, lat] rings.

    A valid polygon has at least 4 points (3 + closing point).
    First and last points must be identical.
    """
    if not polygon or len(polygon) < 1:
        raise InvalidGeometryError(message="Polygon must have at least one ring")

    ring = polygon[0]
    if len(ring) < 4:
        raise InvalidGeometryError(
            message="Polygon ring must have at least 4 coordinate pairs (3 + closing)",
        )

    for point in ring:
        if len(point) != 2:
            raise InvalidGeometryError(message=f"Each point must have 2 coordinates, got {len(point)}")
        validate_coordinates(lat=point[1], lon=point[0])

    if ring[0] != ring[-1]:
        raise InvalidGeometryError(message="Polygon ring must be closed (first == last point)")


def validate_bounding_box(
    lat_min: float, lat_max: float, lon_min: float, lon_max: float,
) -> None:
    """Validate that bounding box coordinates are sane."""
    validate_coordinates(lat_min, lon_min)
    validate_coordinates(lat_max, lon_max)
    if lat_min > lat_max:
        raise InvalidGeometryError(
            message="lat_min must be <= lat_max",
            details={"lat_min": lat_min, "lat_max": lat_max},
        )
    if lon_min > lon_max:
        raise InvalidGeometryError(
            message="lon_min must be <= lon_max",
            details={"lon_min": lon_min, "lon_max": lon_max},
        )


def point_in_bbox(
    lat: float, lon: float,
    lat_min: float, lat_max: float,
    lon_min: float, lon_max: float,
) -> bool:
    """Fast bounding box containment check (no PostGIS required)."""
    return lat_min <= lat <= lat_max and lon_min <= lon <= lon_max


def compute_bbox_from_points(points: list[tuple[float, float]]) -> dict[str, float]:
    """Compute a bounding box from a list of (lat, lon) points."""
    if not points:
        return {"lat_min": 0, "lat_max": 0, "lon_min": 0, "lon_max": 0}
    lats = [p[0] for p in points]
    lons = [p[1] for p in points]
    return {
        "lat_min": min(lats),
        "lat_max": max(lats),
        "lon_min": min(lons),
        "lon_max": max(lons),
    }


def to_wkt_polygon(polygon: list[list[float]]) -> str:
    """Convert GeoJSON-style polygon to WKT for PostGIS insertion."""
    coords = ", ".join(f"{p[0]} {p[1]}" for p in polygon[0])
    return f"POLYGON(({coords}))"
