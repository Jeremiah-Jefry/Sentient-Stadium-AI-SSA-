"""Decision API routes — decision history, explanations, simulations, feedback."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.features.ai_intelligence.api.deps import (
    get_decision_repo,
    get_intelligence_service,
)
from app.features.ai_intelligence.dto.requests import (
    ExplainDecisionRequest,
    SimulateInterventionRequest,
)
from app.features.ai_intelligence.dto.responses import (
    DecisionResponse,
    ExplanationResponse,
    SimulatedInterventionResponse,
)
from app.features.ai_intelligence.repositories.decision_repository import (
    DecisionRepository,
)
from app.features.ai_intelligence.services.intelligence_service import (
    IntelligenceService,
)
from app.shared.result import Success

router = APIRouter(
    prefix="/intelligence/decisions",
    tags=["Decisions"],
)


class PaginatedDecisionResponse(BaseModel):
    items: list[DecisionResponse] = Field(default_factory=list)
    total: int
    page: int
    page_size: int
    total_pages: int


class DecisionFeedbackRequest(BaseModel):
    feedback: str
    rating: int = Field(ge=1, le=5)


@router.get(
    "/{venue_id}",
    response_model=PaginatedDecisionResponse,
    status_code=status.HTTP_200_OK,
)
async def list_decisions(
    venue_id: str,
    status_filter: str | None = Query(None, alias="status"),
    intervention_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    intelligence: IntelligenceService = Depends(get_intelligence_service),
) -> PaginatedDecisionResponse:
    """List decision history for a venue with optional filters."""
    result = await intelligence.get_decision_history(
        venue_id=venue_id,
        status=status_filter,
        page=page,
        page_size=page_size,
    )
    if not isinstance(result, Success):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.message,
        )

    decisions, total = result.value
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    items = [DecisionResponse(**d) for d in decisions]

    return PaginatedDecisionResponse(
        items=items, total=total, page=page,
        page_size=page_size, total_pages=total_pages,
    )


@router.get(
    "/detail/{decision_id}",
    response_model=DecisionResponse,
    status_code=status.HTTP_200_OK,
)
async def get_decision_detail(
    decision_id: str,
    decision_repo: DecisionRepository = Depends(get_decision_repo),
) -> DecisionResponse:
    """Retrieve a single decision by ID."""
    import uuid as _uuid

    d_uuid = _uuid.UUID(decision_id)
    result = await decision_repo.get_by_id(d_uuid)
    if not isinstance(result, Success):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.message,
        )
    d = result.value
    if d is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Decision {decision_id} not found",
        )
    return DecisionResponse(
        id=str(d.id), venue_id=str(d.venue_id),
        zone_id=str(d.zone_id) if d.zone_id else None,
        decision_status=d.decision_status,
        intervention_type=d.intervention_type,
        confidence=d.confidence,
        risk_level_at_decision=d.risk_level_at_decision,
        reasoning=d.reasoning,
        expected_outcome=d.expected_outcome,
        published_at=d.published_at.isoformat() if d.published_at else None,
    )


@router.post(
    "/explain",
    response_model=ExplanationResponse,
    status_code=status.HTTP_200_OK,
)
async def explain_decision(
    req: ExplainDecisionRequest,
    intelligence: IntelligenceService = Depends(get_intelligence_service),
) -> ExplanationResponse:
    """Request a structured explanation for a decision."""
    result = await intelligence.explain_decision(req.decision_id)
    if not isinstance(result, Success):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.message,
        )
    data = result.value
    return ExplanationResponse(
        decision_id=data["decision_id"],
        summary=data["summary"],
        reason=str(data.get("reasoning", "")),
        evidence=data.get("reasoning", {}).get("evidence", []),
        contributing_factors=data.get("reasoning", {}).get("factors", []),
        confidence=data.get("risk_level_at_decision", "") != "",
        alternatives=data.get("alternative_decisions", []),
        tradeoffs=[],
        expected_outcome=str(data.get("expected_outcome", "")),
    )


@router.post(
    "/simulate",
    response_model=SimulatedInterventionResponse,
    status_code=status.HTTP_200_OK,
)
async def simulate_intervention(
    req: SimulateInterventionRequest,
    intelligence: IntelligenceService = Depends(get_intelligence_service),
) -> SimulatedInterventionResponse:
    """Run a what-if intervention simulation."""
    result = await intelligence.simulate_intervention(
        venue_id=req.venue_id,
        intervention_type=req.intervention_type,
        strategy_params=req.strategy_params,
        zone_id=req.zone_id,
    )
    if not isinstance(result, Success):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=result.message,
        )
    data = result.value
    return SimulatedInterventionResponse(
        intervention_type=data["intervention_type"],
        strategy_params=data["strategy_params"],
        simulated_risk_reduction=data["simulated_risk_reduction"],
        simulated_confidence=data["confidence"],
        risk_before=data["risk_before"],
        risk_after=data["risk_after"],
        evaluation_factors=[
            {"factor": "reduction", "value": data["simulated_risk_reduction"]},
            {"factor": "confidence", "value": data["confidence"]},
        ],
    )


@router.post(
    "/{decision_id}/feedback",
    response_model=dict,
    status_code=status.HTTP_200_OK,
)
async def submit_decision_feedback(
    decision_id: str,
    req: DecisionFeedbackRequest,
    decision_repo: DecisionRepository = Depends(get_decision_repo),
) -> dict:
    """Submit volunteer feedback on a decision."""
    import uuid as _uuid

    d_uuid = _uuid.UUID(decision_id)
    result = await decision_repo.get_by_id(d_uuid)
    if not isinstance(result, Success):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.message,
        )
    if result.value is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Decision {decision_id} not found",
        )
    return {
        "decision_id": decision_id,
        "feedback_received": True,
        "rating": req.rating,
        "message": req.feedback,
    }
