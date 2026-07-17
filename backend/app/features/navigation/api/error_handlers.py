"""Navigation API error handlers."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.features.navigation.exceptions import (
    NavigationError,
)


def register_navigation_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(NavigationError)
    async def navigation_error_handler(
        request: Request, exc: NavigationError,
    ) -> JSONResponse:
        status_map = {
            "ROUTE_NOT_FOUND": 404,
            "GRAPH_NOT_LOADED": 503,
            "NODE_NOT_FOUND": 404,
            "ACCESSIBILITY_ROUTE_ERROR": 422,
            "EMERGENCY_ROUTING_ERROR": 500,
            "REPLANNING_ERROR": 500,
            "SIMULATION_ERROR": 500,
            "CACHE_CORRUPTION": 500,
            "CONCURRENCY_CONFLICT": 409,
            "INVALID_ROUTING_PROFILE": 422,
        }
        status = status_map.get(exc.error_code, 500)
        return JSONResponse(
            status_code=status,
            content={
                "error": exc.error_code,
                "message": exc.message,
                "details": exc.details,
            },
        )
