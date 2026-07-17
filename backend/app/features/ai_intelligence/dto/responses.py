from __future__ import annotations

from pydantic import BaseModel, Field


class RiskAssessmentResponse(BaseModel):
    venue_id: str
    zone_id: str | None
    risk_level: str
    risk_score: float
    venue_risk: float
    zone_risk: float
    medical_risk: float
    security_risk: float
    accessibility_risk: float
    transport_risk: float
    weather_risk: float
    risk_factors: dict
    assessed_at: str


class PredictionResponse(BaseModel):
    id: str
    venue_id: str
    zone_id: str | None
    prediction_type: str
    predicted_value: float
    confidence: float
    prediction_window_seconds: int
    predicted_at: str
    valid_until: str
    contributing_factors: list[dict] = Field(default_factory=list)
    evidence_events: list[str] = Field(default_factory=list)
    model_version: str


class PaginatedPredictionResponse(BaseModel):
    items: list[PredictionResponse] = Field(default_factory=list)
    total: int
    page: int
    page_size: int
    total_pages: int


class DecisionResponse(BaseModel):
    id: str
    venue_id: str
    zone_id: str | None
    decision_status: str
    intervention_type: str
    confidence: float
    risk_level_at_decision: str
    reasoning: dict
    expected_outcome: dict
    published_at: str | None


class ExplanationResponse(BaseModel):
    decision_id: str
    summary: str
    reason: str
    evidence: list[dict] = Field(default_factory=list)
    contributing_factors: list[dict] = Field(default_factory=list)
    confidence: float
    alternatives: list[dict] = Field(default_factory=list)
    tradeoffs: list[dict] = Field(default_factory=list)
    expected_outcome: str


class SimulatedInterventionResponse(BaseModel):
    intervention_type: str
    strategy_params: dict
    simulated_risk_reduction: float
    simulated_confidence: float
    risk_before: str
    risk_after: str
    evaluation_factors: list[dict] = Field(default_factory=list)


class IntelligenceStatusResponse(BaseModel):
    active_predictions: int
    active_risk_assessments: int
    pending_decisions: int
    total_interventions_today: int
    pipeline_latency_ms: float
    model_versions: dict[str, str]
    last_assessment_at: str | None


class LiveRiskResponse(BaseModel):
    venue_id: str
    current_risk_level: str
    current_risk_score: float
    zone_risks: list[dict] = Field(default_factory=list)
    trend: str
    updated_at: str
