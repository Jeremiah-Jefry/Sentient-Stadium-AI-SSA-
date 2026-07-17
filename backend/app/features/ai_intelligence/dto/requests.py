from __future__ import annotations

from pydantic import BaseModel, Field


class QueryRiskRequest(BaseModel):
    venue_id: str
    zone_id: str | None = None
    since: str | None = None
    until: str | None = None


class QueryPredictionsRequest(BaseModel):
    venue_id: str
    zone_id: str | None = None
    prediction_type: str | None = None
    min_confidence: float = Field(0.0, ge=0.0, le=1.0)
    page: int = Field(1, ge=1)
    page_size: int = Field(50, ge=1, le=500)


class QueryDecisionsRequest(BaseModel):
    venue_id: str
    status: str | None = None
    intervention_type: str | None = None
    page: int = Field(1, ge=1)
    page_size: int = Field(50, ge=1, le=500)


class ExplainDecisionRequest(BaseModel):
    decision_id: str
    include_alternatives: bool = True
    include_evidence: bool = True


class SimulateInterventionRequest(BaseModel):
    venue_id: str
    zone_id: str | None = None
    intervention_type: str
    strategy_params: dict = Field(default_factory=dict)
    time_horizon_seconds: int = Field(300, ge=30, le=3600)


class RequestReplayAnalysisRequest(BaseModel):
    venue_id: str
    from_timestamp: str
    to_timestamp: str
    prediction_types: list[str] = Field(default_factory=list)
