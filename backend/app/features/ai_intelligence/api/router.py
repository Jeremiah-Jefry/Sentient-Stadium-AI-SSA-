"""API router aggregation for the AI Intelligence Engine module."""

from __future__ import annotations

from fastapi import APIRouter

from app.features.ai_intelligence.api.decision_routes import (
    router as decision_router,
)
from app.features.ai_intelligence.api.explanation_routes import (
    router as explanation_router,
)
from app.features.ai_intelligence.api.prediction_routes import (
    router as prediction_router,
)
from app.features.ai_intelligence.api.risk_routes import router as risk_router
from app.features.ai_intelligence.api.status_routes import router as status_router

ai_intelligence_router = APIRouter(prefix="/api/v1")
ai_intelligence_router.include_router(risk_router)
ai_intelligence_router.include_router(prediction_router)
ai_intelligence_router.include_router(decision_router)
ai_intelligence_router.include_router(explanation_router)
ai_intelligence_router.include_router(status_router)
