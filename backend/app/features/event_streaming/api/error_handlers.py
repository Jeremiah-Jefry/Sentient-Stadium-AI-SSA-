"""Error handlers for Event Streaming module exceptions."""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.features.event_streaming.exceptions import (
    CacheError,
    ConsumerError,
    EventDuplicateError,
    EventExpiredError,
    EventStreamingError,
    EventValidationError,
    FusionError,
    PipelineStageError,
    ReplayError,
    SensorInactiveError,
    SensorNotFoundError,
)


def register_event_streaming_error_handlers(app: FastAPI) -> None:
    """Register all event streaming exception handlers on the FastAPI application."""

    @app.exception_handler(EventValidationError)
    async def handle_event_validation(
        request: Request, exc: EventValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": {"code": exc.error_code, "message": exc.message}},
        )

    @app.exception_handler(EventDuplicateError)
    async def handle_event_duplicate(
        request: Request, exc: EventDuplicateError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"error": {"code": exc.error_code, "message": exc.message}},
        )

    @app.exception_handler(EventExpiredError)
    async def handle_event_expired(
        request: Request, exc: EventExpiredError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_410_GONE,
            content={"error": {"code": exc.error_code, "message": exc.message}},
        )

    @app.exception_handler(PipelineStageError)
    async def handle_pipeline_stage(
        request: Request, exc: PipelineStageError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": {"code": exc.error_code, "message": exc.message}},
        )

    @app.exception_handler(ConsumerError)
    async def handle_consumer_error(
        request: Request, exc: ConsumerError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": {"code": exc.error_code, "message": exc.message}},
        )

    @app.exception_handler(SensorNotFoundError)
    async def handle_sensor_not_found(
        request: Request, exc: SensorNotFoundError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": {"code": exc.error_code, "message": exc.message}},
        )

    @app.exception_handler(SensorInactiveError)
    async def handle_sensor_inactive(
        request: Request, exc: SensorInactiveError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"error": {"code": exc.error_code, "message": exc.message}},
        )

    @app.exception_handler(ReplayError)
    async def handle_replay_error(
        request: Request, exc: ReplayError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": {"code": exc.error_code, "message": exc.message}},
        )

    @app.exception_handler(FusionError)
    async def handle_fusion_error(
        request: Request, exc: FusionError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": {"code": exc.error_code, "message": exc.message}},
        )

    @app.exception_handler(CacheError)
    async def handle_cache_error(
        request: Request, exc: CacheError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": {"code": exc.error_code, "message": exc.message}},
        )

    @app.exception_handler(EventStreamingError)
    async def handle_event_streaming_error(
        request: Request, exc: EventStreamingError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": {"code": exc.error_code, "message": exc.message}},
        )
