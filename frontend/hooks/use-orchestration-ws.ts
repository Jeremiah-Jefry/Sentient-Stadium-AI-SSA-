/**
 * React hook for real-time Orchestration WebSocket connection.
 *
 * Manages connection lifecycle, execution subscriptions, streaming chunk
 * reception, and exponential backoff reconnect.
 */

"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import type {
  OrchestrationWSMessage,
  OrchestrationWSEvent,
  StreamingChunk,
  StreamingEventType,
} from "@/types/orchestration";

const WS_URL =
  process.env.NEXT_PUBLIC_ORCHESTRATION_WS_URL ??
  "ws://localhost:8000/ws/orchestration";

const BASE_RECONNECT_MS = 1000;
const MAX_RECONNECT_MS = 30000;
const MAX_RECONNECT_ATTEMPTS = 20;

interface UseOrchestrationWSReturn {
  connected: boolean;
  chunks: StreamingChunk[];
  latestChunk: StreamingChunk | null;
  eventTypes: StreamingEventType[];
  connect: (token: string) => void;
  disconnect: () => void;
  subscribe: (executionId: string) => void;
  unsubscribe: (executionId: string) => void;
  cancel: (executionId: string) => void;
  clearChunks: () => void;
}

export function useOrchestrationWS(): UseOrchestrationWSReturn {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const tokenRef = useRef<string | null>(null);

  const [connected, setConnected] = useState(false);
  const [chunks, setChunks] = useState<StreamingChunk[]>([]);
  const [latestChunk, setLatestChunk] = useState<StreamingChunk | null>(null);
  const [eventTypes, setEventTypes] = useState<StreamingEventType[]>([]);

  const clearReconnectTimer = useCallback(() => {
    if (reconnectTimer.current !== null) {
      clearTimeout(reconnectTimer.current);
      reconnectTimer.current = null;
    }
  }, []);

  const send = useCallback((msg: OrchestrationWSMessage) => {
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
    tokenRef.current = null;
  }, [clearReconnectTimer]);

  const connect = useCallback(
    (token: string) => {
      clearReconnectTimer();
      reconnectAttempts.current = 0;
      tokenRef.current = token;

      if (wsRef.current) {
        wsRef.current.close();
      }

      const ws = new WebSocket(
        `${WS_URL}?token=${encodeURIComponent(token)}`,
      );
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        reconnectAttempts.current = 0;
      };

      ws.onmessage = (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data) as OrchestrationWSEvent;
          if (data.data) {
            const chunk = data.data;
            setLatestChunk(chunk);
            setChunks((prev) => [...prev, chunk]);
            setEventTypes((prev) => {
              if (prev.includes(chunk.type)) return prev;
              return [...prev, chunk.type];
            });
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
            if (tokenRef.current) {
              connect(tokenRef.current);
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

  const subscribe = useCallback(
    (executionId: string) => {
      send({ action: "subscribe_execution", execution_id: executionId });
    },
    [send],
  );

  const unsubscribe = useCallback(
    (executionId: string) => {
      send({ action: "unsubscribe_execution", execution_id: executionId });
    },
    [send],
  );

  const cancel = useCallback(
    (executionId: string) => {
      send({ action: "cancel_execution", execution_id: executionId });
    },
    [send],
  );

  const clearChunks = useCallback(() => {
    setChunks([]);
    setLatestChunk(null);
    setEventTypes([]);
  }, []);

  useEffect(() => {
    return () => {
      clearReconnectTimer();
      reconnectAttempts.current = MAX_RECONNECT_ATTEMPTS;
      wsRef.current?.close();
    };
  }, [clearReconnectTimer]);

  return {
    connected,
    chunks,
    latestChunk,
    eventTypes,
    connect,
    disconnect,
    subscribe,
    unsubscribe,
    cancel,
    clearChunks,
  };
}
