/**
 * React hook for querying and managing Navigation data.
 * Provides route computation, spatial queries, emergency routing,
 * volunteer assignments, and engine statistics.
 */

"use client";

import { useCallback, useState } from "react";

import type {
  RouteDetailResponse,
  EmergencyRouteResponse,
  NearestEntityResponse,
  NavigationStatsResponse,
} from "@/types/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const REQUEST_TIMEOUT_MS = 15_000;

interface UseNavigationReturn {
  route: RouteDetailResponse | null;
  emergencyRoute: EmergencyRouteResponse | null;
  nearest: NearestEntityResponse | null;
  stats: NavigationStatsResponse | null;
  loading: boolean;
  error: string | null;
  computeRoute: (
    originId: string,
    destinationId: string,
    profile?: string,
    routeType?: string,
  ) => Promise<void>;
  computeEmergencyRoute: (
    startId: string,
    emergencyType: string,
    destinationId?: string,
  ) => Promise<void>;
  findNearest: (
    fromId: string,
    queryType: string,
  ) => Promise<void>;
  fetchStats: () => Promise<void>;
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
        (errorBody as Record<string, unknown>)?.detail ?? `HTTP ${res.status}`;
      throw new Error(String(message));
    }
    if (res.status === 204) return undefined as T;
    return (await res.json()) as T;
  } finally {
    clearTimeout(timeoutId);
  }
}

export function useNavigation(): UseNavigationReturn {
  const [route, setRoute] = useState<RouteDetailResponse | null>(null);
  const [emergencyRoute, setEmergencyRoute] =
    useState<EmergencyRouteResponse | null>(null);
  const [nearest, setNearest] = useState<NearestEntityResponse | null>(null);
  const [stats, setStats] = useState<NavigationStatsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const computeRoute = useCallback(
    async (
      originId: string,
      destinationId: string,
      profile = "spectator",
      routeType = "fastest",
    ) => {
      setLoading(true);
      setError(null);
      try {
        const url = `${API_BASE}/api/v1/navigation/routes/compute`;
        const data = await apiFetch<RouteDetailResponse>(url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            origin_id: originId,
            destination_id: destinationId,
            profile,
            route_type: routeType,
          }),
        });
        setRoute(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  const computeEmergencyRoute = useCallback(
    async (startId: string, emergencyType: string, destinationId?: string) => {
      setLoading(true);
      setError(null);
      try {
        const url = `${API_BASE}/api/v1/navigation/routes/emergency`;
        const data = await apiFetch<EmergencyRouteResponse>(url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            start_id: startId,
            emergency_type: emergencyType,
            destination_id: destinationId,
          }),
        });
        setEmergencyRoute(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  const findNearest = useCallback(
    async (fromId: string, queryType: string) => {
      setLoading(true);
      setError(null);
      try {
        const url = `${API_BASE}/api/v1/navigation/routes/spatial`;
        const data = await apiFetch<NearestEntityResponse>(url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ from_id: fromId, query_type: queryType }),
        });
        setNearest(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  const fetchStats = useCallback(async () => {
    try {
      const url = `${API_BASE}/api/v1/navigation/routes/stats`;
      const data = await apiFetch<NavigationStatsResponse>(url);
      setStats(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    }
  }, []);

  return {
    route,
    emergencyRoute,
    nearest,
    stats,
    loading,
    error,
    computeRoute,
    computeEmergencyRoute,
    findNearest,
    fetchStats,
  };
}
