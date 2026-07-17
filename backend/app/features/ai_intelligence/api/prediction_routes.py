"""Prediction API routes — active predictions, accuracy stats, evaluation."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.features.ai_intelligence.api.deps import (
    get_intelligence_service,
    get_prediction_repo,
)
from app.features.ai_intelligence.dto.responses import (
    PaginatedPredictionResponse,
    PredictionResponse,
)
from app.features.ai_intelligence.repositories.prediction_repository import (
    PredictionRepository,
)
from app.features.ai_intelligence.services.intelligence_service import (
    IntelligenceService,
)
from app.shared.result import Success

router = APIRouter(
    prefix="/intelligence/predictions",
    tags=["Predictions"],
)


@router.get(
    "/{venue_id}",
    response_model=PaginatedPredictionResponse,
    status_code=status.HTTP_200_OK,
)
async def list_predictions(
    venue_id: str,
    zone_id: str | None = Query(None),
    prediction_type: str | None = Query(None),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    intelligence: IntelligenceService = Depends(get_intelligence_service),
) -> PaginatedPredictionResponse:
    """List active predictions for a venue with optional filters."""
    result = await intelligence.get_predictions(
        venue_id=venue_id,
        zone_id=zone_id,
        prediction_type=prediction_type,
        min_confidence=min_confidence,
        page=page,
        page_size=page_size,
    )
    if not isinstance(result, Success):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=result.message,
        )

    predictions, total = result.value
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    items = [PredictionResponse(**p) for p in predictions]

    return PaginatedPredictionResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/accuracy/{venue_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
)
async def get_prediction_accuracy(
    venue_id: str,
    prediction_type: str | None = Query(None),
    prediction_repo: PredictionRepository = Depends(get_prediction_repo),
) -> dict:
    """Retrieve prediction accuracy statistics for a venue."""
    import uuid as _uuid

    v_uuid = _uuid.UUID(venue_id)
    result = await prediction_repo.get_accuracy_stats(
        venue_id=v_uuid, prediction_type=prediction_type,
    )
    if not isinstance(result, Success):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=result.message,
        )
    return result.value


@router.post(
    "/evaluate/{prediction_id}",
    response_model=PredictionResponse,
    status_code=status.HTTP_200_OK,
)
async def evaluate_prediction(
    prediction_id: str,
    actual_value: float = Query(..., description="Ground truth value"),
    prediction_repo: PredictionRepository = Depends(get_prediction_repo),
) -> PredictionResponse:
    """Evaluate a prediction against the actual observed value."""
    import uuid as _uuid

    p_uuid = _uuid.UUID(prediction_id)
    result = await prediction_repo.evaluate_accuracy(
        prediction_id=p_uuid, actual_value=actual_value,
    )
    if not isinstance(result, Success):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=result.message,
        )
    p = result.value
    return PredictionResponse(
        id=str(p.id),
        venue_id=str(p.venue_id),
        zone_id=str(p.zone_id) if p.zone_id else None,
        prediction_type=p.prediction_type,
        predicted_value=p.predicted_value,
        confidence=p.confidence,
        prediction_window_seconds=p.prediction_window_seconds,
        predicted_at=p.predicted_at.isoformat(),
        valid_until=p.valid_until.isoformat(),
        contributing_factors=p.contributing_factors,
        evidence_events=p.evidence_events,
        model_version=p.model_version,
    )
