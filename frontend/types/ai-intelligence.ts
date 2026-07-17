/**
 * Shared TypeScript types for the AI Intelligence Engine module.
 * Mirrors the backend DTOs for type safety across the full stack.
 */

export type RiskLevel = "green" | "yellow" | "orange" | "red" | "critical";

export type PredictionType =
  | "bottleneck"
  | "congestion"
  | "queue_growth"
  | "dangerous_density"
  | "medical_overload"
  | "volunteer_shortage"
  | "exit_saturation"
  | "transport_congestion"
  | "wheelchair_blockage"
  | "lost_child"
  | "cleaning_overload"
  | "security_pressure";

export type DecisionStatus =
  | "candidate"
  | "simulated"
  | "selected"
  | "published"
  | "executed"
  | "rejected"
  | "expired";

export type InterventionType =
  | "do_nothing"
  | "redirect_volunteers"
  | "open_secondary_gate"
  | "deploy_medical"
  | "close_corridor"
  | "reverse_flow"
  | "split_crowd"
  | "multilingual_announcement"
  | "increase_security"
  | "accessibility_priority_routing";

export type MatchPhase =
  | "pre_match"
  | "kickoff"
  | "first_half"
  | "halftime"
  | "second_half"
  | "extra_time"
  | "penalty_shootout"
  | "post_match"
  | "rain_delay"
  | "evacuation";

export type Trend = "improving" | "stable" | "deteriorating";

export type ConfidenceSource =
  | "sensor_agreement"
  | "historical_similarity"
  | "model_agreement"
  | "data_freshness"
  | "evidence_count";

export type ObservationType = "realtime" | "replay" | "simulation";

export interface RiskAssessmentResponse {
  venue_id: string;
  zone_id: string | null;
  risk_level: RiskLevel;
  risk_score: number;
  venue_risk: number;
  zone_risk: number;
  medical_risk: number;
  security_risk: number;
  accessibility_risk: number;
  transport_risk: number;
  weather_risk: number;
  risk_factors: Record<string, unknown>;
  assessed_at: string;
}

export interface ContributingFactor {
  factor: string;
  weight: number;
  value: number;
  description?: string;
}

export interface PredictionResponse {
  id: string;
  venue_id: string;
  zone_id: string | null;
  prediction_type: PredictionType;
  predicted_value: number;
  confidence: number;
  prediction_window_seconds: number;
  predicted_at: string;
  valid_until: string;
  contributing_factors: ContributingFactor[];
  evidence_events: string[];
  model_version: string;
}

export interface PaginatedPredictionResponse {
  items: PredictionResponse[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface DecisionResponse {
  id: string;
  venue_id: string;
  zone_id: string | null;
  decision_status: DecisionStatus;
  intervention_type: InterventionType;
  confidence: number;
  risk_level_at_decision: RiskLevel;
  reasoning: Record<string, unknown>;
  expected_outcome: Record<string, unknown>;
  published_at: string | null;
}

export interface PaginatedDecisionResponse {
  items: DecisionResponse[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ExplanationEvidence {
  event_id: string;
  event_type: string;
  source: string;
  timestamp: string;
  relevance: number;
  description?: string;
}

export interface ExplanationResponse {
  decision_id: string;
  summary: string;
  reason: string;
  evidence: ExplanationEvidence[];
  contributing_factors: ContributingFactor[];
  confidence: number;
  alternatives: AlternativeDecision[];
  tradeoffs: Tradeoff[];
  expected_outcome: string;
}

export interface AlternativeDecision {
  intervention_type: string;
  confidence: number;
  rejection_reason: string;
  simulated_risk_reduction: number;
}

export interface Tradeoff {
  factor: string;
  pros: string;
  cons: string;
}

export interface SimulatedInterventionResponse {
  intervention_type: string;
  strategy_params: Record<string, unknown>;
  simulated_risk_reduction: number;
  simulated_confidence: number;
  risk_before: RiskLevel;
  risk_after: RiskLevel;
  evaluation_factors: EvaluationFactor[];
}

export interface EvaluationFactor {
  factor: string;
  value: number;
}

export interface IntelligenceStatusResponse {
  active_predictions: number;
  active_risk_assessments: number;
  pending_decisions: number;
  total_interventions_today: number;
  pipeline_latency_ms: number;
  model_versions: Record<string, string>;
  last_assessment_at: string | null;
}

export interface ZoneRisk {
  zone_id: string;
  zone_name: string;
  risk_level: RiskLevel;
  risk_score: number;
}

export interface LiveRiskResponse {
  venue_id: string;
  current_risk_level: RiskLevel;
  current_risk_score: number;
  zone_risks: ZoneRisk[];
  trend: Trend;
  updated_at: string;
}

export interface ConfidenceBreakdown {
  sensor_agreement: number;
  historical_similarity: number;
  model_agreement: number;
  data_freshness: number;
  evidence_count: number;
}

export interface IntelligenceWSMessage {
  action: "subscribe_venue" | "unsubscribe_venue";
  venue_id?: string;
  token?: string;
}

export interface IntelligenceWSEvent {
  type: "risk_update" | "new_prediction" | "recommendation" | "ping";
  venue_id: string;
  data: Record<string, unknown>;
  timestamp?: string;
}
