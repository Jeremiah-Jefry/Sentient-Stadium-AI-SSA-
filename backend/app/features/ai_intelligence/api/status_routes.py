"""Status API routes — engine status, health check, and monitoring metrics."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.features.ai_intelligence.api.deps import (
    get_intelligence_service,
    get_monitoring_service,
)
from app.features.ai_intelligence.dto.responses import IntelligenceStatusResponse
from app.features.ai_intelligence.services.intelligence_service import (
    IntelligenceService,
)
from app.features.ai_intelligence.services.monitoring_service import (
    MonitoringService,
)

router = APIRouter(
    prefix="/intelligence/status",
    tags=["Intelligence Status"],
)


@router.get(
    "/",
    response_model=IntelligenceStatusResponse,
    status_code=status.HTTP_200_OK,
)
async def get_intelligence_status(
    intelligence: IntelligenceService = Depends(get_intelligence_service),
    monitoring: MonitoringService = Depends(get_monitoring_service),
) -> IntelligenceStatusResponse:
    """Retrieve the current intelligence engine status."""
    status_data = intelligence.status
    latency = monitoring.stats.get("latency_avg_ms", 0.0)

    return IntelligenceStatusResponse(
        active_predictions=0,
        active_risk_assessments=0,
        pending_decisions=0,
        total_interventions_today=status_data.get("total_processed", 0),
        pipeline_latency_ms=latency,
        model_versions={
            "risk_engine": "1.0.0",
            "prediction_engine": "1.0.0",
            "confidence_engine": "1.0.0",
            "explainability_engine": "1.0.0",
        },
        last_assessment_at=status_data.get("last_assessment_at"),
    )


@router.get(
    "/health",
    response_model=dict,
    status_code=status.HTTP_200_OK,
)
async def health_check(
    intelligence: IntelligenceService = Depends(get_intelligence_service),
) -> dict:
    """Health check for the intelligence engine."""
    status_data = intelligence.status
    return {
        "status": "healthy" if status_data.get("engine_active") else "degraded",
        "module": "ai_intelligence",
        "engine_active": status_data.get("engine_active", False),
        "total_processed": status_data.get("total_processed", 0),
        "total_errors": status_data.get("total_errors", 0),
    }


@router.get(
    "/monitoring",
    response_model=dict,
    status_code=status.HTTP_200_OK,
)
async def get_monitoring_metrics(
    monitoring: MonitoringService = Depends(get_monitoring_service),
) -> dict:
    """Retrieve monitoring metrics for prediction accuracy and operational KPIs."""
    return monitoring.stats
