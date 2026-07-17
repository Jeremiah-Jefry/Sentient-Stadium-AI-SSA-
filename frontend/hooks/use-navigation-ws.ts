/**
 * React hook for real-time Navigation WebSocket connection.
 *
 * Manages connection lifecycle, venue subscriptions, and incoming
 * route update/replan notification pushes with exponential backoff reconnect.
 */

"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import type { NavigationWSMessage, NavigationWSEvent } from "@/types/navigation";

const WS_URL =
  process.env.NEXT_PUBLIC_NAVIGATION_WS_URL ??
  "ws://localhost:8000/ws/navigation";

const BASE_RECONNECT_MS = 1000;
const MAX_RECONNECT_MS = 30000;
const MAX_RECONNECT_ATTEMPTS = 20;

interface UseNavigationWSReturn {
  connected: boolean;
  latestRouteUpdate: Record<string, unknown> | null;
  latestReplan: Record<string, unknown> | null;
  latestCongestion: Record<string, unknown> | null;
  connect: (venueId: string, token: string) => void;
  disconnect: () => void;
}

export function useNavigationWS(): UseNavigationWSReturn {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const venueIdRef = useRef<string | null>(null);

  const [connected, setConnected] = useState(false);
  const [latestRouteUpdate, setLatestRouteUpdate] =
    useState<Record<string, unknown> | null>(null);
  const [latestReplan, setLatestReplan] =
    useState<Record<string, unknown> | null>(null);
  const [latestCongestion, setLatestCongestion] =
    useState<Record<string, unknown> | null>(null);

  const clearReconnectTimer = useCallback(() => {
    if (reconnectTimer.current !== null) {
      clearTimeout(reconnectTimer.current);
      reconnectTimer.current = null;
    }
  }, []);

  const send = useCallback((msg: NavigationWSMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg));
    }
  }, []);

  const disconnect = useCallback(() => {
    clearReconnectTimer();
    reconnectAttempts.current = MAX_RECONNECT_ATTEMPTS;
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setConnected(false);
    venueIdRef.current = null;
  }, [clearReconnectTimer]);

  const connect = useCallback(
    (venueId: string, token: string) => {
      clearReconnectTimer();
      reconnectAttempts.current = 0;
      venueIdRef.current = venueId;

      if (wsRef.current) {
        wsRef.current.close();
      }

      const ws = new WebSocket(`${WS_URL}?token=${encodeURIComponent(token)}`);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        reconnectAttempts.current = 0;
        send({ action: "subscribe_venue", venue_id: venueId });
      };

      ws.onmessage = (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data) as NavigationWSEvent;
          if (data.type === "route_update" && data.data) {
            setLatestRouteUpdate(data.data);
          } else if (data.type === "replan_notification" && data.data) {
            setLatestReplan(data.data);
          } else if (data.type === "congestion_alert" && data.data) {
            setLatestCongestion(data.data);
          }
        } catch {
          // Non-JSON messages are ignored
        }
      };

      ws.onclose = () => {
        setConnected(false);
        if (reconnectAttempts.current < MAX_RECONNECT_ATTEMPTS) {
          const delay = Math.min(
            BASE_RECONNECT_MS * 2 ** reconnectAttempts.current,
            MAX_RECONNECT_MS,
          );
          reconnectTimer.current = setTimeout(() => {
            reconnectAttempts.current += 1;
            if (venueIdRef.current) {
              connect(venueIdRef.current, token);
            }
          }, delay);
        }
      };

      ws.onerror = () => {
        ws.close();
      };
    },
    [clearReconnectTimer, send],
  );

  useEffect(() => {
    return () => {
      clearReconnectTimer();
      reconnectAttempts.current = MAX_RECONNECT_ATTEMPTS;
      wsRef.current?.close();
    };
  }, [clearReconnectTimer]);

  return {
    connected,
    latestRouteUpdate,
    latestReplan,
    latestCongestion,
    connect,
    disconnect,
  };
}
