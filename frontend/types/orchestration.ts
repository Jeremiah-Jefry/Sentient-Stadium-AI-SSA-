/**
 * Shared TypeScript types for the Orchestration Engine module.
 * Mirrors the backend DTOs for type safety across the full stack.
 */

export type RequestType =
  | "volunteer_request"
  | "admin_request"
  | "system_event"
  | "realtime_event"
  | "prediction_trigger"
  | "emergency"
  | "accessibility_request"
  | "navigation_request";

export type IntentType =
  | "crowd_management"
  | "navigation"
  | "emergency_response"
  | "accessibility"
  | "medical"
  | "resource_allocation"
  | "information_query"
  | "incident_response"
  | "evacuation"
  | "weather_advisory"
  | "security"
  | "operational";

export type ExecutionStatus =
  | "pending"
  | "planning"
  | "executing"
  | "aggregating"
  | "validating"
  | "completed"
  | "failed"
  | "cancelled"
  | "timeout";

export type AgentStatus =
  | "available"
  | "busy"
  | "degraded"
  | "offline"
  | "error"
  | "warming_up";

export type SafetyLevel =
  | "safe"
  | "warning"
  | "dangerous"
  | "critical"
  | "requires_human_review";

export type StreamingEventType =
  | "progress"
  | "agent_status"
  | "partial_result"
  | "reasoning_update"
  | "confidence_update"
  | "error"
  | "complete";

export type ReasoningStage =
  | "observe"
  | "think"
  | "plan"
  | "execute"
  | "critique"
  | "improve"
  | "validate"
  | "explain";

export type PipelineStage =
  | "understand"
  | "plan"
  | "execute"
  | "validate"
  | "explain"
  | "respond";

export interface OrchestratorRequest {
  request_type: RequestType;
  intent: IntentType;
  venue_id: string;
  zone_id?: string;
  payload: Record<string, unknown>;
  priority?: number;
  requester_id?: string;
  context?: Record<string, unknown>;
}

export interface ConfidenceReport {
  overall: number;
  per_agent: Record<string, number>;
  agreement_score: number;
  reasoning_quality: number;
  evidence_strength: number;
  safety_confidence: number;
  knowledge_base_coverage: number;
  limiting_factors: string[];
}

export interface SafetyReport {
  level: SafetyLevel;
  score: number;
  violations: string[];
  warnings: string[];
  requires_human_review: boolean;
  human_review_reason: string | null;
  safety_checks_passed: string[];
}

export interface EvidenceItem {
  source: string;
  type: string;
  content: string;
  weight: number;
  timestamp: string;
  metadata: Record<string, unknown>;
}

export interface ReasoningStageResult {
  stage: ReasoningStage;
  status: ExecutionStatus;
  output: Record<string, unknown>;
  confidence: number;
  evidence: EvidenceItem[];
  duration_ms: number | null;
  started_at: string | null;
  completed_at: string | null;
}

export interface ReasoningChain {
  chain_id: string;
  execution_id: string;
  stages: ReasoningStageResult[];
  overall_reasoning: string;
  started_at: string;
  completed_at: string | null;
}

export interface ExecutionStep {
  step_id: string;
  agent_name: string;
  action: string;
  parameters: Record<string, unknown>;
  depends_on: string[];
  status: ExecutionStatus;
  result: Record<string, unknown> | null;
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number | null;
  error: string | null;
}

export interface ExecutionPlan {
  plan_id: string;
  execution_id: string;
  steps: ExecutionStep[];
  total_steps: number;
  parallel_groups: string[][];
  estimated_duration_ms: number;
  created_at: string;
}

export interface OrchestratorResponse {
  execution_id: string;
  status: ExecutionStatus;
  intent: IntentType;
  request_type: RequestType;
  venue_id: string;
  result: Record<string, unknown> | null;
  confidence_report: ConfidenceReport;
  safety_report: SafetyReport;
  reasoning_chain: ReasoningChain;
  execution_plan: ExecutionPlan;
  agents_involved: string[];
  started_at: string;
  completed_at: string | null;
  duration_ms: number | null;
}

export interface AgentMetadata {
  name: string;
  display_name: string;
  description: string;
  capabilities: string[];
  input_types: string[];
  output_types: string[];
  version: string;
  health_score: number;
  avg_response_ms: number;
}

export interface RegisteredAgent {
  name: string;
  metadata: AgentMetadata;
  status: AgentStatus;
  health_score: number;
  current_load: number;
  max_load: number;
  last_heartbeat: string;
  total_executions: number;
  success_rate: number;
  avg_response_ms: number;
}

export interface StreamingChunk {
  type: StreamingEventType;
  execution_id: string;
  data: Record<string, unknown>;
  timestamp: string;
  sequence: number;
}

export type { ContributingFactor, AlternativeDecision, Tradeoff, Explanation, ToolMetadata, MetricsSummary, ExecutionGraph, ExecutionGraphNode, ExecutionGraphEdge, OrchestrationWSMessage, OrchestrationWSEvent } from "./orchestration-detail";
