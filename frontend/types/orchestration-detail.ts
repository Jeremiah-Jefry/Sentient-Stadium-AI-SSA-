/**
 * Extended TypeScript types for the Orchestration Engine module.
 * Contains supporting types used by the core orchestration interfaces.
 */

export interface ContributingFactor {
  factor: string;
  weight: number;
  value: number;
  description?: string;
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

export interface Explanation {
  summary: string;
  detailed_reasoning: string;
  evidence: import("./orchestration").EvidenceItem[];
  contributing_factors: ContributingFactor[];
  alternatives: AlternativeDecision[];
  tradeoffs: Tradeoff[];
}

export interface ToolMetadata {
  name: string;
  description: string;
  input_schema: Record<string, unknown>;
  output_schema: Record<string, unknown>;
  agent_name: string;
}

export interface MetricsSummary {
  total_executions: number;
  successful_executions: number;
  failed_executions: number;
  cancelled_executions: number;
  avg_duration_ms: number;
  p95_duration_ms: number;
  avg_confidence: number;
  active_executions: number;
  agents_available: number;
  agents_busy: number;
  agents_offline: number;
  last_updated: string;
}

export interface ExecutionGraph {
  nodes: ExecutionGraphNode[];
  edges: ExecutionGraphEdge[];
}

export interface ExecutionGraphNode {
  id: string;
  agent_name: string;
  action: string;
  status: string;
  wave: number;
  x: number;
  y: number;
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number | null;
}

export interface ExecutionGraphEdge {
  source: string;
  target: string;
  type: "dependency" | "data_flow" | "trigger";
}

export interface OrchestrationWSMessage {
  action: "subscribe_execution" | "unsubscribe_execution" | "cancel_execution";
  execution_id?: string;
  token?: string;
}

export interface OrchestrationWSEvent {
  type: string;
  execution_id: string;
  data: import("./orchestration").StreamingChunk;
  timestamp: string;
}
