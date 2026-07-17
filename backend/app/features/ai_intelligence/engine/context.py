"""Pipeline context and intermediate data structures for the intelligence pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SituationAssessment:
    """Output of Stage 1: Realtime Situation Assessment."""

    venue_id: str
    zone_id: str | None
    current_density: float
    flow_rate: float
    occupancy_percent: float
    active_sensors: int
    recent_events: list[dict]
    match_phase: str
    behavior_modifiers: dict
    timestamp: float


@dataclass
class BehaviourAnalysis:
    """Output of Stage 2: Crowd Behaviour Analysis."""

    movement_pattern: str
    flow_health: float
    crowd_stability: float
    bottleneck_risk: float
    anomalies: list[dict]
    zone_graph_impacts: list[dict]


@dataclass
class PredictionBundle:
    """Output of Stage 3: Short-Term Prediction."""

    predictions: list[dict]
    overall_confidence: float
    time_horizons: list[int]
    model_versions: dict[str, str]


@dataclass
class RiskBundle:
    """Output of Stage 4: Risk Scoring."""

    overall_risk_level: str
    overall_risk_score: float
    domain_risks: dict[str, float]
    risk_factors: dict[str, float]
    confidence: float


@dataclass
class SimulatedIntervention:
    """Output of Stage 5: Intervention Simulation."""

    intervention_type: str
    strategy_params: dict
    simulated_risk_reduction: float
    simulated_confidence: float
    risk_before: str
    risk_after: str
    evaluation_factors: list[dict]
    side_effects: list[str]
    resource_cost: float


@dataclass
class SelectedDecision:
    """Output of Stage 6: Decision Selection."""

    intervention_type: str
    intervention_params: dict
    confidence: float
    risk_reduction: float
    reasoning: dict
    alternatives_rejected: list[dict]
    resource_requirement: str


@dataclass
class IntelligenceOutput:
    """Output of Stage 7: Explainable AI."""

    explanation: dict
    volunteer_briefing: str
    evidence: list[dict]
    contributing_factors: list[dict]


@dataclass
class IntelligenceContext:
    """Mutable context flowing through all 8 pipeline stages."""

    triggering_event: object
    venue_id: str
    zone_id: str | None = None

    situation: SituationAssessment | None = None
    behaviour: BehaviourAnalysis | None = None
    predictions: PredictionBundle | None = None
    risk: RiskBundle | None = None
    interventions: list[SimulatedIntervention] = field(default_factory=list)
    decision: SelectedDecision | None = None
    intelligence: IntelligenceOutput | None = None
    published: bool = False

    pipeline_start_ms: float = 0.0
    stage_timings: dict[str, float] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def has_critical_failure(self) -> bool:
        """Return True if any stage produced a critical error."""
        return any("CRITICAL" in err for err in self.errors)

    def stage_failed(self, stage_name: str) -> bool:
        """Check if a specific stage recorded an error."""
        prefix = f"[{stage_name}]"
        return any(err.startswith(prefix) for err in self.errors)

    def record_error(self, stage_name: str, message: str) -> None:
        """Append a timestamped stage error."""
        self.errors.append(f"[{stage_name}] {message}")

    def summary(self) -> dict:
        """Return a serialisable summary of the full pipeline state."""
        return {
            "venue_id": self.venue_id,
            "zone_id": self.zone_id,
            "published": self.published,
            "risk_level": self.risk.overall_risk_level if self.risk else None,
            "decision": self.decision.intervention_type if self.decision else None,
            "stage_timings_ms": dict(self.stage_timings),
            "error_count": len(self.errors),
        }
