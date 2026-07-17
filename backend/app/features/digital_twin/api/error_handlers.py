"""Error handlers for Digital Twin module exceptions."""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

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


def register_digital_twin_error_handlers(app: FastAPI) -> None:
    """Register all digital twin exception handlers on the FastAPI application."""

    @app.exception_handler(EntityNotFoundError)
    async def handle_entity_not_found(
        request: Request, exc: EntityNotFoundError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": {"code": exc.error_code, "message": exc.message}},
        )

    @app.exception_handler(ZoneNotFoundError)
    async def handle_zone_not_found(
        request: Request, exc: ZoneNotFoundError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": {"code": exc.error_code, "message": exc.message}},
        )

    @app.exception_handler(VenueNotFoundError)
    async def handle_venue_not_found(
        request: Request, exc: VenueNotFoundError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": {"code": exc.error_code, "message": exc.message}},
        )

    @app.exception_handler(EdgeNotFoundError)
    async def handle_edge_not_found(
        request: Request, exc: EdgeNotFoundError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": {"code": exc.error_code, "message": exc.message}},
        )

    @app.exception_handler(InvalidGeometryError)
    async def handle_invalid_geometry(
        request: Request, exc: InvalidGeometryError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": {"code": exc.error_code, "message": exc.message}},
        )

    @app.exception_handler(InvalidCoordinateError)
    async def handle_invalid_coordinates(
        request: Request, exc: InvalidCoordinateError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": {"code": exc.error_code, "message": exc.message}},
        )

    @app.exception_handler(PathNotFoundError)
    async def handle_path_not_found(
        request: Request, exc: PathNotFoundError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": {"code": exc.error_code, "message": exc.message}},
        )

    @app.exception_handler(CapacityExceededError)
    async def handle_capacity_exceeded(
        request: Request, exc: CapacityExceededError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"error": {"code": exc.error_code, "message": exc.message}},
        )

    @app.exception_handler(EntityValidationError)
    async def handle_entity_validation(
        request: Request, exc: EntityValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": {"code": exc.error_code, "message": exc.message}},
        )

    @app.exception_handler(CyclicZoneError)
    async def handle_cyclic_zone(
        request: Request, exc: CyclicZoneError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"error": {"code": exc.error_code, "message": exc.message}},
        )

    @app.exception_handler(DigitalTwinError)
    async def handle_digital_twin_error(
        request: Request, exc: DigitalTwinError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": {"code": exc.error_code, "message": exc.message}},
        )
