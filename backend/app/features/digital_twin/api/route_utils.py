"""Shared route utilities for Digital Twin API handlers."""

from __future__ import annotations

from fastapi import HTTPException, status

from app.shared.result import Failure, Result


def unwrap_or_raise(result: Result, error_code: str = "OPERATION_FAILED") -> object:
    """Extract the value from a Success result or raise an HTTPException.

    Route handlers should use this instead of directly accessing result.value
    to prevent AttributeError on Failure results.
    """
    if isinstance(result, Failure):
        status_code = _map_error_code(result.error_code)
        raise HTTPException(
            status_code=status_code,
            detail={"error": {"code": result.error_code, "message": result.message}},
        )
    return result.value


def _map_error_code(error_code: str) -> int:
    """Map domain error codes to HTTP status codes."""
    mapping = {
        "ENTITY_NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "ZONE_NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "VENUE_NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "EDGE_NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "PATH_NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "CAPACITY_EXCEEDED": status.HTTP_409_CONFLICT,
        "INVALID_GEOMETRY": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "INVALID_COORDINATES": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "ENTITY_VALIDATION_FAILED": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "CYCLIC_ZONE_HIERARCHY": status.HTTP_409_CONFLICT,
    }
    return mapping.get(error_code, status.HTTP_400_BAD_REQUEST)
