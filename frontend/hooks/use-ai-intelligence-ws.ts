/**
 * React hook for real-time AI Intelligence WebSocket connection.
 *
 * Manages connection lifecycle, venue subscriptions, and incoming
 * risk/prediction/recommendation pushes with exponential backoff reconnect.
 */

"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import type {
  IntelligenceWSMessage,
  IntelligenceWSEvent,
  RiskAssessmentResponse,
  PredictionResponse,
  DecisionResponse,
} from "@/types/ai-intelligence";

const WS_URL =
  process.env.NEXT_PUBLIC_INTELLIGENCE_WS_URL ??
  "ws://localhost:8000/ws/intelligence";

const BASE_RECONNECT_MS = 1000;
const MAX_RECONNECT_MS = 30000;
const MAX_RECONNECT_ATTEMPTS = 20;

interface UseAIWSReturn {
  connected: boolean;
  latestRisk: RiskAssessmentResponse | null;
  latestPrediction: PredictionResponse | null;
  latestRecommendation: DecisionResponse | null;
  connect: (venueId: string, token: string) => void;
  disconnect: () => void;
}

export function useAIIntelligenceWS(): UseAIWSReturn {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const venueIdRef = useRef<string | null>(null);

  const [connected, setConnected] = useState(false);
  const [latestRisk, setLatestRisk] =
    useState<RiskAssessmentResponse | null>(null);
  const [latestPrediction, setLatestPrediction] =
    useState<PredictionResponse | null>(null);
  const [latestRecommendation, setLatestRecommendation] =
    useState<DecisionResponse | null>(null);

  const clearReconnectTimer = useCallback(() => {
    if (reconnectTimer.current !== null) {
      clearTimeout(reconnectTimer.current);
      reconnectTimer.current = null;
    }
  }, []);

  const send = useCallback((msg: IntelligenceWSMessage) => {
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
          const data = JSON.parse(event.data) as IntelligenceWSEvent;
          if (data.type === "risk_update" && data.data) {
            setLatestRisk(data.data as unknown as RiskAssessmentResponse);
          } else if (data.type === "new_prediction" && data.data) {
            setLatestPrediction(
              data.data as unknown as PredictionResponse,
            );
          } else if (data.type === "recommendation" && data.data) {
            setLatestRecommendation(
              data.data as unknown as DecisionResponse,
            );
          }
        } catch {
          // Non-JSON messages (ping/pong, subscription confirmations) are ignored
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
    latestRisk,
    latestPrediction,
    latestRecommendation,
    connect,
    disconnect,
  };
}
