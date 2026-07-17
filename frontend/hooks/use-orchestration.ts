/**
 * React hook for querying and managing Orchestration Engine data.
 * Provides execution management, agent status, and metrics.
 */

"use client";

import { useCallback, useState } from "react";

import type {
  OrchestratorRequest,
  OrchestratorResponse,
  RegisteredAgent,
  MetricsSummary,
} from "@/types/orchestration";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const REQUEST_TIMEOUT_MS = 30_000;

interface UseOrchestrationReturn {
  execution: OrchestratorResponse | null;
  agents: RegisteredAgent[];
  metrics: MetricsSummary | null;
  loading: boolean;
  error: string | null;
  execute: (request: OrchestratorRequest) => Promise<OrchestratorResponse | null>;
  cancelExecution: (executionId: string) => Promise<boolean>;
  getExecution: (executionId: string) => Promise<OrchestratorResponse | null>;
  getAgentStatus: () => Promise<void>;
  getMetrics: () => Promise<void>;
}

async function apiFetch<T>(
  url: string,
  options?: RequestInit,
): Promise<T> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const res = await fetch(url, { ...options, signal: controller.signal });
    if (!res.ok) {
      const errorBody = await res.json().catch(() => null);
      const message =
        (errorBody as Record<string, unknown>)?.detail ??
        `HTTP ${res.status}`;
      throw new Error(String(message));
    }
    if (res.status === 204) return undefined as T;
    return (await res.json()) as T;
  } finally {
    clearTimeout(timeoutId);
  }
}

export function useOrchestration(): UseOrchestrationReturn {
  const [execution, setExecution] =
    useState<OrchestratorResponse | null>(null);
  const [agents, setAgents] = useState<RegisteredAgent[]>([]);
  const [metrics, setMetrics] = useState<MetricsSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const execute = useCallback(
    async (
      request: OrchestratorRequest,
    ): Promise<OrchestratorResponse | null> => {
      setLoading(true);
      setError(null);
      try {
        const url = `${API_BASE}/api/v1/orchestration/execute`;
        const data = await apiFetch<OrchestratorResponse>(url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(request),
        });
        setExecution(data);
        return data;
      } catch (err) {
        const message = err instanceof Error ? err.message : "Unknown error";
        setError(message);
        return null;
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  const cancelExecution = useCallback(
    async (executionId: string): Promise<boolean> => {
      setLoading(true);
      setError(null);
      try {
        const url = `${API_BASE}/api/v1/orchestration/execute/${executionId}/cancel`;
        await apiFetch<void>(url, { method: "POST" });
        return true;
      } catch (err) {
        const message = err instanceof Error ? err.message : "Unknown error";
        setError(message);
        return false;
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  const getExecution = useCallback(
    async (executionId: string): Promise<OrchestratorResponse | null> => {
      setLoading(true);
      setError(null);
      try {
        const url = `${API_BASE}/api/v1/orchestration/execute/${executionId}`;
        const data = await apiFetch<OrchestratorResponse>(url, {
          method: "GET",
        });
        setExecution(data);
        return data;
      } catch (err) {
        const message = err instanceof Error ? err.message : "Unknown error";
        setError(message);
        return null;
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  const getAgentStatus = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const url = `${API_BASE}/api/v1/orchestration/agents`;
      const data = await apiFetch<RegisteredAgent[]>(url, { method: "GET" });
      setAgents(data);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown error";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  const getMetrics = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const url = `${API_BASE}/api/v1/orchestration/metrics`;
      const data = await apiFetch<MetricsSummary>(url, { method: "GET" });
      setMetrics(data);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown error";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    execution,
    agents,
    metrics,
    loading,
    error,
    execute,
    cancelExecution,
    getExecution,
    getAgentStatus,
    getMetrics,
  };
}
