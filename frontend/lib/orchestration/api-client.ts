/**
 * Typed API client for the StadiumMind Orchestration Engine backend.
 *
 * Handles execution requests, agent management, monitoring, streaming,
 * and decision history. Follows the same pattern as the Digital Twin API client.
 */

import type {
  OrchestratorRequest,
  OrchestratorResponse,
  RegisteredAgent,
  MetricsSummary,
  ExecutionGraph,
  ExecutionStatus,
  SafetyLevel,
} from "@/types/orchestration";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

const REQUEST_TIMEOUT_MS = 30_000;

let accessToken: string | null = null;

export function setOrchestationToken(token: string | null): void {
  accessToken = token;
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({
      error: { code: "UNKNOWN_ERROR", message: `HTTP ${response.status}` },
    }));
    throw new Error(
      errorBody.error?.message ?? `Request failed: ${response.status}`,
    );
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  timeout?: number;
}

async function apiRequest<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { method = "GET", body, timeout = REQUEST_TIMEOUT_MS } = options;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (accessToken) headers["Authorization"] = `Bearer ${accessToken}`;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });
    return await handleResponse<T>(response);
  } finally {
    clearTimeout(timeoutId);
  }
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ExecutionDetailResponse {
  id: string;
  request_id: string;
  status: ExecutionStatus;
  strategy: string | null;
  recommendation: string | null;
  confidence: number | null;
  reasoning: Record<string, unknown> | null;
  evidence: unknown[] | null;
  agents_used: unknown[] | null;
  alternatives: unknown[] | null;
  explanation: Record<string, unknown> | null;
  total_duration_ms: number | null;
  steps_completed: number;
  steps_failed: number;
  steps: ExecutionStepResponse[];
  created_at: string | null;
}

export interface ExecutionStepResponse {
  id: string;
  agent_id: string | null;
  action: string | null;
  status: string;
  duration_ms: number | null;
  error_message: string | null;
}

export interface AgentStatusResponse {
  total_agents: number;
  status_distribution: Record<string, number>;
  agents: Array<{
    agent_id: string;
    name: string;
    status: string;
    health_score: number;
    current_load: number;
  }>;
}

export interface AgentHealthResponse {
  total_agents: number;
  status_distribution: Record<string, number>;
  avg_health: number;
  total_load: number;
  healthy_count: number;
  unhealthy_agents: Array<{
    agent_id: string;
    name: string;
    health_score: number;
    status: string;
  }>;
}

export interface SystemHealthResponse {
  status: "healthy" | "degraded" | "unhealthy";
  agents: Record<string, unknown>;
  tools: Record<string, unknown>;
  execution_health: Record<string, string>;
  metrics_summary: {
    total_executions: number;
    success_rate: number;
    avg_confidence: number;
  };
}

export interface DecisionEntry {
  id: string;
  execution_id: string;
  request_id: string;
  decision: string;
  reasoning: string | null;
  confidence: number;
  agents_involved: unknown[] | null;
  safety_level: SafetyLevel | null;
  created_at: string | null;
}

export interface ConflictResolutionResponse {
  conflict_id: string;
  resolution_strategy: string;
  participants: unknown[];
  resolution: Record<string, unknown>;
  confidence: number;
}

export const orchestrationApi = {
  execute: (request: OrchestratorRequest) =>
    apiRequest<OrchestratorResponse>("/orchestration/execute", {
      method: "POST",
      body: request,
    }),

  executeStreaming: (request: OrchestratorRequest) =>
    apiRequest<{
      execution_id: string;
      stream_session_id: string;
      status: string;
    }>("/orchestration/execute/streaming", {
      method: "POST",
      body: request,
    }),

  getExecution: (executionId: string) =>
    apiRequest<ExecutionDetailResponse>(
      `/orchestration/execution/${executionId}`,
    ),

  cancelExecution: (executionId: string) =>
    apiRequest<{ execution_id: string; status: string }>(
      `/orchestration/cancel/${executionId}`,
      { method: "POST" },
    ),

  getExecutionHistory: (
    params: {
      status?: ExecutionStatus;
      page?: number;
      page_size?: number;
    } = {},
  ) => {
    const searchParams = new URLSearchParams();
    if (params.status) searchParams.set("status", params.status);
    if (params.page) searchParams.set("page", String(params.page));
    if (params.page_size) searchParams.set("page_size", String(params.page_size));
    const qs = searchParams.toString();
    return apiRequest<PaginatedResponse<ExecutionDetailResponse>>(
      `/orchestration/history${qs ? `?${qs}` : ""}`,
    );
  },

  getDecisionHistory: (requestId: string) =>
    apiRequest<{ items: DecisionEntry[]; total: number }>(
      `/orchestration/decisions/${requestId}`,
    ),
};

export const orchestrationAgentApi = {
  listAgents: () =>
    apiRequest<RegisteredAgent[]>("/orchestration/agents"),

  getAgentStatus: () =>
    apiRequest<AgentStatusResponse>("/orchestration/agents/status"),

  getAgentHealth: () =>
    apiRequest<AgentHealthResponse>("/orchestration/agents/health"),

  getAgent: (agentId: string) =>
    apiRequest<RegisteredAgent>(`/orchestration/agents/${agentId}`),

  updateAgentStatus: (
    agentId: string,
    status: string,
  ) =>
    apiRequest<{ agent_id: string; status: string; message: string }>(
      `/orchestration/agents/${agentId}/status?new_status=${status}`,
      { method: "PUT" },
    ),
};

export const orchestrationMonitoringApi = {
  getMetrics: () =>
    apiRequest<MetricsSummary>("/orchestration/monitoring/metrics"),

  getExecutionGraph: (executionId: string) =>
    apiRequest<ExecutionGraph>(
      `/orchestration/monitoring/graph/${executionId}`,
    ),

  getSystemHealth: () =>
    apiRequest<SystemHealthResponse>("/orchestration/monitoring/health"),

  listTools: () =>
    apiRequest<Array<{
      tool_id: string;
      name: string;
      description: string;
      version: string;
      timeout_seconds: number;
      cache_ttl_seconds: number;
      max_retries: number;
    }>>("/orchestration/tools"),
};
