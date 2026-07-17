/**
 * React hook for sensor data queries and fusion status.
 */

"use client";

import { useCallback, useEffect, useState } from "react";

import type { FusedReading, Sensor, SensorHealth } from "@/types/event-streaming";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface UseSensorDataOptions {
  venueId?: string;
  zoneId?: string;
  autoRefresh?: boolean;
  refreshIntervalMs?: number;
}

interface UseSensorDataReturn {
  sensors: Sensor[];
  health: SensorHealth | null;
  fusedReadings: Record<string, FusedReading>;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export function useSensorData({
  venueId,
  zoneId,
  autoRefresh = false,
  refreshIntervalMs = 10000,
}: UseSensorDataOptions = {}): UseSensorDataReturn {
  const [sensors, setSensors] = useState<Sensor[]>([]);
  const [health, setHealth] = useState<SensorHealth | null>(null);
  const [fusedReadings, setFusedReadings] = useState<Record<string, FusedReading>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchHealth = useCallback(async () => {
    if (!venueId) return;
    try {
      const res = await fetch(`${API_BASE}/api/v1/sensors/health/${venueId}`);
      if (res.ok) setHealth(await res.json());
    } catch {
      // Non-critical
    }
  }, [venueId]);

  const fetchFusionStatus = useCallback(async () => {
    if (!venueId || !zoneId) return;
    try {
      const params = new URLSearchParams({ zone_id: zoneId });
      const res = await fetch(`${API_BASE}/api/v1/sensors/fusion-status/${venueId}?${params}`);
      if (res.ok) setFusedReadings(await res.json());
    } catch {
      // Non-critical
    }
  }, [venueId, zoneId]);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      await Promise.all([fetchHealth(), fetchFusionStatus()]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, [fetchHealth, fetchFusionStatus]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    if (!autoRefresh) return;
    const timer = setInterval(refresh, refreshIntervalMs);
    return () => clearInterval(timer);
  }, [autoRefresh, refreshIntervalMs, refresh]);

  return { sensors, health, fusedReadings, loading, error, refresh };
}
