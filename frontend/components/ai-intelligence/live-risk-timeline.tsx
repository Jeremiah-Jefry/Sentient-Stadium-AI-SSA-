/**
 * LiveRiskTimeline - Real-time scrolling risk update feed.
 *
 * Uses useAIIntelligenceWS for live updates, displays risk changes
 * with timestamps and color-coded levels, auto-scrolls to latest.
 */

"use client";

import { memo, useEffect, useRef, useState } from "react";

import { useAIIntelligenceWS } from "@/hooks/use-ai-intelligence-ws";
import type { RiskLevel } from "@/types/ai-intelligence";

interface LiveRiskTimelineProps {
  venueId: string;
  token: string;
}

interface TimelineEntry {
  id: string;
  level: RiskLevel;
  score: number;
  assessedAt: string;
}

const RISK_DOT_COLORS: Record<RiskLevel, string> = {
  green: "#4caf50",
  yellow: "#ff9800",
  orange: "#ff5722",
  red: "#f44336",
  critical: "#9c27b0",
};

const MAX_ENTRIES = 100;

let entryCounter = 0;

function LiveRiskTimelineInner({ venueId, token }: LiveRiskTimelineProps) {
  const { connected, latestRisk, connect, disconnect } =
    useAIIntelligenceWS();
  const [entries, setEntries] = useState<TimelineEntry[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);
  const prevScoreRef = useRef<number | null>(null);

  useEffect(() => {
    connect(venueId, token);
    return () => disconnect();
  }, [venueId, token, connect, disconnect]);

  useEffect(() => {
    if (!latestRisk) return;
    if (latestRisk.risk_score === prevScoreRef.current) return;
    prevScoreRef.current = latestRisk.risk_score;

    entryCounter += 1;
    const entry: TimelineEntry = {
      id: `entry-${entryCounter}`,
      level: latestRisk.risk_level,
      score: latestRisk.risk_score,
      assessedAt: latestRisk.assessed_at ?? new Date().toISOString(),
    };

    setEntries((prev) => [entry, ...prev].slice(0, MAX_ENTRIES));
  }, [latestRisk]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = 0;
    }
  }, [entries.length]);

  return (
    <div
      role="region"
      aria-label="Live risk timeline"
      style={styles.container}
    >
      <div style={styles.header}>
        <h3 style={styles.title}>Live Risk Feed</h3>
        <span style={styles.statusIndicator}>
          <span
            style={{
              ...styles.statusDot,
              backgroundColor: connected ? "#4caf50" : "#f44336",
            }}
          />
          {connected ? "Connected" : "Disconnected"}
        </span>
      </div>

      <div ref={scrollRef} style={styles.scrollArea} role="log" aria-live="polite">
        {entries.length === 0 && (
          <p style={styles.emptyMessage}>Waiting for risk updates...</p>
        )}
        {entries.map((entry) => (
          <div key={entry.id} style={styles.entry}>
            <span
              style={{
                ...styles.dot,
                backgroundColor: RISK_DOT_COLORS[entry.level],
              }}
              aria-hidden="true"
            />
            <div style={styles.entryContent}>
              <div style={styles.entryHeader}>
                <span
                  style={{
                    ...styles.levelBadge,
                    color: RISK_DOT_COLORS[entry.level],
                    backgroundColor: `${RISK_DOT_COLORS[entry.level]}1a`,
                  }}
                >
                  {entry.level.toUpperCase()}
                </span>
                <time style={styles.timestamp} dateTime={entry.assessedAt}>
                  {new Date(entry.assessedAt).toLocaleTimeString()}
                </time>
              </div>
              <span style={styles.score}>Score: {entry.score.toFixed(2)}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    backgroundColor: "#1a1a2e",
    border: "1px solid #2d2d44",
    borderRadius: 8,
    overflow: "hidden",
    display: "flex",
    flexDirection: "column",
    height: "100%",
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "12px 16px",
    borderBottom: "1px solid #2d2d44",
  },
  title: {
    fontSize: 14,
    fontWeight: 600,
    color: "#e0e0e0",
    margin: 0,
  },
  statusIndicator: {
    display: "flex",
    alignItems: "center",
    gap: 6,
    fontSize: 12,
    color: "#9e9e9e",
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: "50%",
  },
  scrollArea: {
    flex: 1,
    overflowY: "auto",
    padding: 8,
  },
  emptyMessage: {
    textAlign: "center",
    color: "#757575",
    fontSize: 13,
    padding: 24,
    margin: 0,
  },
  entry: {
    display: "flex",
    alignItems: "flex-start",
    gap: 10,
    padding: "8px 8px",
    borderBottom: "1px solid #1f1f35",
  },
  dot: {
    width: 10,
    height: 10,
    borderRadius: "50%",
    marginTop: 4,
    flexShrink: 0,
  },
  entryContent: {
    display: "flex",
    flexDirection: "column",
    gap: 4,
    flex: 1,
  },
  entryHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  levelBadge: {
    fontSize: 11,
    fontWeight: 600,
    padding: "2px 8px",
    borderRadius: 4,
    letterSpacing: "0.5px",
  },
  timestamp: {
    fontSize: 11,
    color: "#757575",
    fontVariantNumeric: "tabular-nums",
  },
  score: {
    fontSize: 12,
    color: "#bdbdbd",
    fontVariantNumeric: "tabular-nums",
  },
};

export const LiveRiskTimeline = memo(LiveRiskTimelineInner);
