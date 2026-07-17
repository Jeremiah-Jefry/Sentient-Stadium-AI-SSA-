"""API router aggregation for the Orchestration Engine module."""

from __future__ import annotations

from fastapi import APIRouter

from app.features.orchestration.api.agent_routes import (
    router as agent_router,
)
from app.features.orchestration.api.monitoring_routes import (
    router as monitoring_router,
)
from app.features.orchestration.api.request_routes import (
    router as request_router,
)

orchestration_router = APIRouter(prefix="/api/v1")
orchestration_router.include_router(request_router)
orchestration_router.include_router(agent_router)
orchestration_router.include_router(monitoring_router)
