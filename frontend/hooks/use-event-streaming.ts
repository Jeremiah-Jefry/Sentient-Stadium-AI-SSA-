/**
 * React hook for querying and managing event streaming data.
 * Provides paginated event queries, stream status, and dead letter access.
 */

"use client";

import { useCallback, useEffect, useState } from "react";

import type {
  DeadLetterEvent,
  EventSummary,
  PaginatedEventResponse,
  StreamStatus,
} from "@/types/event-streaming";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface UseEventStreamingOptions {
  venueId?: string;
  category?: string;
  page?: number;
  pageSize?: number;
  autoRefresh?: boolean;
  refreshIntervalMs?: number;
}

interface UseEventStreamingReturn {
  events: EventSummary[];
  total: number;
  totalPages: number;
  loading: boolean;
  error: string | null;
  streamStatus: StreamStatus | null;
  deadLetters: DeadLetterEvent[];
  refresh: () => Promise<void>;
  refreshStatus: () => Promise<void>;
  loadDeadLetters: () => Promise<void>;
}

export function useEventStreaming({
  venueId,
  category,
  page = 1,
  pageSize = 50,
  autoRefresh = false,
  refreshIntervalMs = 5000,
}: UseEventStreamingOptions = {}): UseEventStreamingReturn {
  const [events, setEvents] = useState<EventSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [streamStatus, setStreamStatus] = useState<StreamStatus | null>(null);
  const [deadLetters, setDeadLetters] = useState<DeadLetterEvent[]>([]);

  const fetchEvents = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
      if (venueId) params.set("venue_id", venueId);
      if (category) params.set("category", category);

      const res = await fetch(`${API_BASE}/api/v1/events/query?${params}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: PaginatedEventResponse = await res.json();
      setEvents(data.items);
      setTotal(data.total);
      setTotalPages(data.total_pages);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, [venueId, category, page, pageSize]);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/streaming/status`);
      if (res.ok) {
        setStreamStatus(await res.json());
      }
    } catch {
      // Silently fail — status is non-critical
    }
  }, []);

  const fetchDeadLetters = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/events/dead-letter`);
      if (res.ok) {
        setDeadLetters(await res.json());
      }
    } catch {
      // Silently fail
    }
  }, []);

  useEffect(() => {
    fetchEvents();
  }, [fetchEvents]);

  useEffect(() => {
    if (!autoRefresh) return;
    const timer = setInterval(() => {
      fetchEvents();
      fetchStatus();
    }, refreshIntervalMs);
    return () => clearInterval(timer);
  }, [autoRefresh, refreshIntervalMs, fetchEvents, fetchStatus]);

  return {
    events,
    total,
    totalPages,
    loading,
    error,
    streamStatus,
    deadLetters,
    refresh: fetchEvents,
    refreshStatus: fetchStatus,
    loadDeadLetters: fetchDeadLetters,
  };
}
