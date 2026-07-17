/**
 * React hook for real-time event streaming WebSocket connection.
 *
 * Manages connection lifecycle, venue/category/entity subscriptions,
 * and automatic reconnection on disconnect.
 */

"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import type {
  EventStreamEvent,
  EventStreamMessage,
} from "@/types/event-streaming";

const WS_URL =
  process.env.NEXT_PUBLIC_EVENT_STREAM_WS_URL ??
  "ws://localhost:8000/ws/events";

const RECONNECT_DELAY_MS = 3000;
const MAX_RECONNECT_ATTEMPTS = 10;

interface UseEventStreamWebSocketOptions {
  venueId?: string;
  categories?: string[];
  entityIds?: string[];
  onEvent?: (event: EventStreamEvent) => void;
  enabled?: boolean;
}

interface UseEventStreamWebSocketReturn {
  isConnected: boolean;
  lastEvent: EventStreamEvent | null;
  subscribeVenue: (venueId: string) => void;
  subscribeCategory: (category: string) => void;
  subscribeEntity: (entityId: string) => void;
  unsubscribeVenue: (venueId: string) => void;
  unsubscribeCategory: (category: string) => void;
  unsubscribeEntity: (entityId: string) => void;
}

export function useEventStreamWebSocket({
  venueId,
  categories = [],
  entityIds = [],
  onEvent,
  enabled = true,
}: UseEventStreamWebSocketOptions = {}): UseEventStreamWebSocketReturn {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [isConnected, setIsConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<EventStreamEvent | null>(null);

  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  const send = useCallback((msg: EventStreamMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg));
    }
  }, []);

  const subscribeVenue = useCallback(
    (id: string) => send({ action: "subscribe_venue", venue_id: id }),
    [send],
  );

  const subscribeCategory = useCallback(
    (cat: string) => send({ action: "subscribe_category", category: cat }),
    [send],
  );

  const subscribeEntity = useCallback(
    (id: string) => send({ action: "subscribe_entity", entity_id: id }),
    [send],
  );

  const unsubscribeVenue = useCallback(
    (id: string) => send({ action: "unsubscribe_venue", venue_id: id }),
    [send],
  );

  const unsubscribeCategory = useCallback(
    (cat: string) => send({ action: "unsubscribe_category", category: cat }),
    [send],
  );

  const unsubscribeEntity = useCallback(
    (id: string) => send({ action: "unsubscribe_entity", entity_id: id }),
    [send],
  );

  useEffect(() => {
    if (!enabled) return;

    function connect() {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        reconnectAttempts.current = 0;

        if (venueId) {
          send({ action: "subscribe_venue", venue_id: venueId });
        }
        for (const cat of categories) {
          send({ action: "subscribe_category", category: cat });
        }
        for (const eid of entityIds) {
          send({ action: "subscribe_entity", entity_id: eid });
        }
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as EventStreamEvent;
          if (data.event_type) {
            setLastEvent(data);
            onEventRef.current?.(data);
          }
        } catch {
          // Non-JSON messages (subscription confirmations) are silently ignored
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        if (reconnectAttempts.current < MAX_RECONNECT_ATTEMPTS) {
          reconnectTimer.current = setTimeout(() => {
            reconnectAttempts.current += 1;
            connect();
          }, RECONNECT_DELAY_MS);
        }
      };

      ws.onerror = () => {
        ws.close();
      };
    }

    connect();

    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [enabled, venueId, categories, entityIds, send]);

  return {
    isConnected,
    lastEvent,
    subscribeVenue,
    subscribeCategory,
    subscribeEntity,
    unsubscribeVenue,
    unsubscribeCategory,
    unsubscribeEntity,
  };
}
