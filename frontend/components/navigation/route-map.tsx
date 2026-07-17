/**
 * RouteMap - Interactive route visualization component.
 * Displays computed route on a stylized stadium map with
 * step indicators, turn-by-turn guidance, and accessibility overlays.
 */

"use client";

import { memo, useMemo } from "react";

import type { RouteResponse, RouteStep } from "@/types/navigation";

interface RouteMapProps {
  route: RouteResponse;
  showAlternatives?: boolean;
  accessibilityOverlay?: boolean;
}

const GRADE_COLORS: Record<string, string> = {
  "A+": "#4caf50",
  A: "#4caf50",
  "A-": "#66bb6a",
  "B+": "#8bc34a",
  B: "#cddc39",
  "C": "#ff9800",
  D: "#f44336",
  F: "#9c27b0",
};

function RouteMapInner({
  route,
  showAlternatives = false,
  accessibilityOverlay = false,
}: RouteMapProps) {
  const gradeColor = GRADE_COLORS[route.grade] ?? "#9e9e9e";

  const totalTime = useMemo(() => {
    const min = Math.floor(route.total_time_seconds / 60);
    const sec = Math.round(route.total_time_seconds % 60);
    return `${min}m ${sec}s`;
  }, [route.total_time_seconds]);

  const totalDist = useMemo(() => {
    return route.total_distance_meters < 1000
      ? `${Math.round(route.total_distance_meters)}m`
      : `${(route.total_distance_meters / 1000).toFixed(1)}km`;
  }, [route.total_distance_meters]);

  return (
    <div style={styles.container} role="region" aria-label="Route map">
      <div style={styles.header}>
        <span style={{ ...styles.grade, color: gradeColor }}>
          {route.grade}
        </span>
        <div style={styles.meta}>
          <span>{totalTime}</span>
          <span style={styles.separator}>|</span>
          <span>{totalDist}</span>
          <span style={styles.separator}>|</span>
          <span>{route.steps.length} steps</span>
        </div>
      </div>

      <div style={styles.timeline} role="list" aria-label="Route steps">
        {route.steps.map((step: RouteStep, idx: number) => (
          <div key={step.node_id} style={styles.step} role="listitem">
            <div style={styles.stepIndicator}>
              <div
                style={{
                  ...styles.dot,
                  backgroundColor: idx === 0 ? "#4caf50" :
                    idx === route.steps.length - 1 ? "#f44336" : "#666",
                }}
              />
              {idx < route.steps.length - 1 && <div style={styles.line} />}
            </div>
            <div style={styles.stepContent}>
              <span style={styles.stepName}>
                {step.name || `Node ${idx + 1}`}
              </span>
              <span style={styles.stepType}>{step.entity_type}</span>
              {step.edge_type && (
                <span style={styles.stepEdge}>{step.edge_type}</span>
              )}
            </div>
          </div>
        ))}
      </div>

      <div style={styles.scores}>
        <ScoreBar label="Safety" value={route.safety_score} />
        <ScoreBar label="Access" value={route.accessibility_score} />
        <ScoreBar label="Crowd" value={1 - route.crowd_exposure} />
        <ScoreBar label="Confidence" value={route.confidence} />
      </div>
    </div>
  );
}

function ScoreBar({ label, value }: { label: string; value: number }) {
  const pct = Math.max(0, Math.min(100, value * 100));
  const color = value > 0.7 ? "#4caf50" : value > 0.4 ? "#ff9800" : "#f44336";
  return (
    <div style={styles.scoreRow}>
      <span style={styles.scoreLabel}>{label}</span>
      <div style={styles.scoreTrack}>
        <div style={{ ...styles.scoreFill, width: `${pct}%`, backgroundColor: color }} />
      </div>
      <span style={styles.scoreValue}>{Math.round(pct)}%</span>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: { width: "100%", padding: 12 },
  header: { display: "flex", alignItems: "center", gap: 12, marginBottom: 12 },
  grade: { fontSize: 28, fontWeight: 800 },
  meta: { display: "flex", gap: 4, fontSize: 13, color: "#aaa" },
  separator: { color: "#555" },
  timeline: { display: "flex", flexDirection: "column", gap: 0, marginBottom: 12 },
  step: { display: "flex", gap: 10, minHeight: 36 },
  stepIndicator: { display: "flex", flexDirection: "column", alignItems: "center", width: 16 },
  dot: { width: 10, height: 10, borderRadius: "50%", marginTop: 4 },
  line: { flex: 1, width: 2, backgroundColor: "#444", marginTop: 2 },
  stepContent: { display: "flex", flexDirection: "column", gap: 2 },
  stepName: { fontSize: 13, fontWeight: 500, color: "#e0e0e0" },
  stepType: { fontSize: 11, color: "#888" },
  stepEdge: { fontSize: 10, color: "#666", fontStyle: "italic" },
  scores: { display: "flex", flexDirection: "column", gap: 6 },
  scoreRow: { display: "flex", alignItems: "center", gap: 8 },
  scoreLabel: { width: 70, fontSize: 11, color: "#aaa", textAlign: "right" },
  scoreTrack: { flex: 1, height: 6, backgroundColor: "#2d2d2d", borderRadius: 3 },
  scoreFill: { height: "100%", borderRadius: 3, transition: "width 0.4s ease" },
  scoreValue: { width: 36, fontSize: 11, color: "#aaa", textAlign: "right" },
};

export const RouteMap = memo(RouteMapInner);
