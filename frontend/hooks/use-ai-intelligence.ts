/**
 * React hook for querying and managing AI Intelligence data.
 * Provides risk assessments, predictions, decisions, explanations,
 * intervention simulation, and engine status.
 */

"use client";

import { useCallback, useState } from "react";

import type {
  RiskAssessmentResponse,
  PredictionResponse,
  DecisionResponse,
  ExplanationResponse,
  SimulatedInterventionResponse,
  IntelligenceStatusResponse,
  PaginatedPredictionResponse,
  PaginatedDecisionResponse,
} from "@/types/ai-intelligence";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const REQUEST_TIMEOUT_MS = 15_000;

interface UseAIReturn {
  risk: RiskAssessmentResponse | null;
  predictions: PredictionResponse[];
  decisions: DecisionResponse[];
  explanation: ExplanationResponse | null;
  status: IntelligenceStatusResponse | null;
  loading: boolean;
  error: string | null;
  fetchRisk: (venueId: string, zoneId?: string) => Promise<void>;
  fetchPredictions: (
    venueId: string,
    params?: Record<string, string | number>,
  ) => Promise<void>;
  fetchDecisions: (
    venueId: string,
    params?: Record<string, string | number>,
  ) => Promise<void>;
  explainDecision: (decisionId: string) => Promise<void>;
  simulateIntervention: (
    venueId: string,
    interventionType: string,
    params: Record<string, unknown>,
  ) => Promise<SimulatedInterventionResponse | null>;
  fetchStatus: () => Promise<void>;
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

export function useAIIntelligence(): UseAIReturn {
  const [risk, setRisk] = useState<RiskAssessmentResponse | null>(null);
  const [predictions, setPredictions] = useState<PredictionResponse[]>([]);
  const [decisions, setDecisions] = useState<DecisionResponse[]>([]);
  const [explanation, setExplanation] = useState<ExplanationResponse | null>(
    null,
  );
  const [status, setStatus] = useState<IntelligenceStatusResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchRisk = useCallback(
    async (venueId: string, zoneId?: string) => {
      setLoading(true);
      setError(null);
      try {
        const params = new URLSearchParams();
        if (zoneId) params.set("zone_id", zoneId);
        const qs = params.toString();
        const url = `${API_BASE}/api/v1/intelligence/risk/current/${venueId}${qs ? `?${qs}` : ""}`;
        const data = await apiFetch<RiskAssessmentResponse>(url);
        setRisk(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  const fetchPredictions = useCallback(
    async (venueId: string, params?: Record<string, string | number>) => {
      setLoading(true);
      setError(null);
      try {
        const searchParams = new URLSearchParams();
        if (params) {
          for (const [key, value] of Object.entries(params)) {
            if (value !== undefined && value !== null && value !== "") {
              searchParams.set(key, String(value));
            }
          }
        }
        const qs = searchParams.toString();
        const url = `${API_BASE}/api/v1/intelligence/predictions/${venueId}${qs ? `?${qs}` : ""}`;
        const data = await apiFetch<PaginatedPredictionResponse>(url);
        setPredictions(data.items);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  const fetchDecisions = useCallback(
    async (venueId: string, params?: Record<string, string | number>) => {
      setLoading(true);
      setError(null);
      try {
        const searchParams = new URLSearchParams();
        if (params) {
          for (const [key, value] of Object.entries(params)) {
            if (value !== undefined && value !== null && value !== "") {
              searchParams.set(key, String(value));
            }
          }
        }
        const qs = searchParams.toString();
        const url = `${API_BASE}/api/v1/intelligence/decisions/${venueId}${qs ? `?${qs}` : ""}`;
        const data = await apiFetch<PaginatedDecisionResponse>(url);
        setDecisions(data.items);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  const explainDecision = useCallback(async (decisionId: string) => {
    setLoading(true);
    setError(null);
    try {
      const url = `${API_BASE}/api/v1/intelligence/explanations/decision/${decisionId}`;
      const data = await apiFetch<ExplanationResponse>(url);
      setExplanation(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, []);

  const simulateIntervention = useCallback(
    async (
      venueId: string,
      interventionType: string,
      params: Record<string, unknown>,
    ): Promise<SimulatedInterventionResponse | null> => {
      setLoading(true);
      setError(null);
      try {
        const url = `${API_BASE}/api/v1/intelligence/decisions/simulate`;
        const data = await apiFetch<SimulatedInterventionResponse>(url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            venue_id: venueId,
            intervention_type: interventionType,
            strategy_params: params,
          }),
        });
        return data;
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
        return null;
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  const fetchStatus = useCallback(async () => {
    try {
      const url = `${API_BASE}/api/v1/intelligence/status/`;
      const data = await apiFetch<IntelligenceStatusResponse>(url);
      setStatus(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    }
  }, []);

  return {
    risk,
    predictions,
    decisions,
    explanation,
    status,
    loading,
    error,
    fetchRisk,
    fetchPredictions,
    fetchDecisions,
    explainDecision,
    simulateIntervention,
    fetchStatus,
  };
}
