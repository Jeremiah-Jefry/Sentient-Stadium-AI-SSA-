"""Explanation API routes — decision and risk explanations."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.features.ai_intelligence.api.deps import (
    get_intelligence_service,
)
from app.features.ai_intelligence.dto.responses import ExplanationResponse
from app.features.ai_intelligence.services.intelligence_service import (
    IntelligenceService,
)
from app.shared.result import Success

router = APIRouter(
    prefix="/intelligence/explanations",
    tags=["Explanations"],
)


@router.get(
    "/decision/{decision_id}",
    response_model=ExplanationResponse,
    status_code=status.HTTP_200_OK,
)
async def get_decision_explanation(
    decision_id: str,
    intelligence: IntelligenceService = Depends(get_intelligence_service),
) -> ExplanationResponse:
    """Retrieve a full explanation for a specific decision."""
    result = await intelligence.explain_decision(decision_id)
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
        confidence=0.0,
        alternatives=data.get("alternative_decisions", []),
        tradeoffs=[],
        expected_outcome=str(data.get("expected_outcome", "")),
    )


@router.get(
    "/risk/{venue_id}",
    response_model=ExplanationResponse,
    status_code=status.HTTP_200_OK,
)
async def get_risk_explanation(
    venue_id: str,
    zone_id: str | None = Query(None),
    intelligence: IntelligenceService = Depends(get_intelligence_service),
) -> ExplanationResponse:
    """Retrieve an explanation of the current risk assessment for a venue."""
    result = await intelligence.get_current_risk(venue_id, zone_id)
    if not isinstance(result, Success):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=result.message,
        )
    risk_data = result.value

    from app.features.ai_intelligence.explainability.explainability_engine import (
        ExplainabilityEngine,
    )

    engine = ExplainabilityEngine()
    explanation = engine.explain_risk(
        risk_assessment=risk_data,
        events=[],
        context={"venue_id": venue_id, "zone_id": zone_id},
    )

    return ExplanationResponse(
        decision_id="",
        summary=explanation.summary,
        reason=explanation.reason,
        evidence=explanation.evidence,
        contributing_factors=explanation.contributing_factors,
        confidence=explanation.confidence,
        alternatives=[],
        tradeoffs=explanation.tradeoffs,
        expected_outcome=explanation.expected_outcome,
    )
