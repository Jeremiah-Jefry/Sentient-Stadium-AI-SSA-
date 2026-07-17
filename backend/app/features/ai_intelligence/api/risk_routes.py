"""Risk assessment API routes — current risk, history, and trend analysis."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.features.ai_intelligence.api.deps import (
    get_intelligence_service,
    get_risk_repo,
)
from app.features.ai_intelligence.dto.responses import (
    RiskAssessmentResponse,
)
from app.features.ai_intelligence.repositories.risk_repository import RiskRepository
from app.features.ai_intelligence.services.intelligence_service import (
    IntelligenceService,
)
from app.shared.result import Success

router = APIRouter(prefix="/intelligence/risk", tags=["Risk Assessment"])


@router.get(
    "/current/{venue_id}",
    response_model=RiskAssessmentResponse,
    status_code=status.HTTP_200_OK,
)
async def get_current_risk(
    venue_id: str,
    zone_id: str | None = Query(None, description="Optional zone filter"),
    intelligence: IntelligenceService = Depends(get_intelligence_service),
) -> RiskAssessmentResponse:
    """Retrieve the current risk assessment for a venue or zone."""
    result = await intelligence.get_current_risk(venue_id, zone_id)
    if not isinstance(result, Success):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=result.message,
        )
    data = result.value
    return RiskAssessmentResponse(**data)


@router.get(
    "/history/{venue_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
)
async def get_risk_history(
    venue_id: str,
    zone_id: str | None = Query(None),
    since: str | None = Query(None, description="ISO 8601 start time"),
    until: str | None = Query(None, description="ISO 8601 end time"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    risk_repo: RiskRepository = Depends(get_risk_repo),
) -> dict:
    """Retrieve paginated risk history for a venue."""
    import uuid as _uuid
    from datetime import datetime

    v_uuid = _uuid.UUID(venue_id)
    z_uuid = _uuid.UUID(zone_id) if zone_id else None
    since_dt = (
        datetime.fromisoformat(since) if since else None
    )
    until_dt = (
        datetime.fromisoformat(until) if until else None
    )

    result = await risk_repo.get_history(
        venue_id=v_uuid, zone_id=z_uuid,
        since=since_dt, until=until_dt,
        page=page, page_size=page_size,
    )
    if not isinstance(result, Success):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=result.message,
        )

    records, total = result.value
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    items = [
        {
            "id": str(r.id),
            "venue_id": str(r.venue_id),
            "zone_id": str(r.zone_id) if r.zone_id else None,
            "risk_level": r.risk_level,
            "risk_score": r.risk_score,
            "risk_factors": r.risk_factors,
            "assessed_at": r.assessed_at.isoformat(),
        }
        for r in records
    ]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.get(
    "/trend/{venue_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
)
async def get_risk_trend(
    venue_id: str,
    zone_id: str | None = Query(None),
    lookback_minutes: int = Query(60, ge=5, le=1440),
    risk_repo: RiskRepository = Depends(get_risk_repo),
) -> dict:
    """Analyze risk trend over a recent time window."""
    import uuid as _uuid

    v_uuid = _uuid.UUID(venue_id)
    z_uuid = _uuid.UUID(zone_id) if zone_id else None

    result = await risk_repo.get_trend(
        venue_id=v_uuid, zone_id=z_uuid,
        lookback_minutes=lookback_minutes,
    )
    if not isinstance(result, Success):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=result.message,
        )
    return result.value
