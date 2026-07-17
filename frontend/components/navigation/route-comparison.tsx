/**
 * RouteComparison - Side-by-side route comparison cards.
 * Shows multiple route options with metrics, grades, and tradeoffs
 * to help users choose the best route for their needs.
 */

"use client";

import { memo, useMemo } from "react";

import type { RouteResponse } from "@/types/navigation";

interface RouteComparisonProps {
  routes: RouteResponse[];
  selectedIndex?: number;
  onSelect?: (index: number) => void;
}

const GRADE_COLORS: Record<string, string> = {
  "A+": "#4caf50",
  A: "#4caf50",
  "A-": "#66bb6a",
  "B+": "#8bc34a",
  B: "#cddc39",
  C: "#ff9800",
  D: "#f44336",
  F: "#9c27b0",
};

function RouteComparisonInner({
  routes,
  selectedIndex = 0,
  onSelect,
}: RouteComparisonProps) {
  const formatted = useMemo(
    () =>
      routes.map((r) => ({
        ...r,
        timeMin: Math.floor(r.total_time_seconds / 60),
        timeSec: Math.round(r.total_time_seconds % 60),
        distDisplay:
          r.total_distance_meters < 1000
            ? `${Math.round(r.total_distance_meters)}m`
            : `${(r.total_distance_meters / 1000).toFixed(1)}km`,
        gradeColor: GRADE_COLORS[r.grade] ?? "#9e9e9e",
      })),
    [routes],
  );

  return (
    <div style={styles.container} role="radiogroup" aria-label="Route options">
      {formatted.map((route, idx) => (
        <button
          key={route.route_id}
          type="button"
          role="radio"
          aria-checked={idx === selectedIndex}
          aria-label={`Route ${idx + 1}: ${route.timeMin}m ${route.timeSec}s, grade ${route.grade}`}
          style={{
            ...styles.card,
            borderColor: idx === selectedIndex ? "#2196f3" : "#333",
            backgroundColor: idx === selectedIndex ? "#1a2332" : "#1e1e1e",
          }}
          onClick={() => onSelect?.(idx)}
        >
          <div style={styles.cardHeader}>
            <span style={{ ...styles.grade, color: route.gradeColor }}>
              {route.grade}
            </span>
            <span style={styles.time}>
              {route.timeMin}m {route.timeSec}s
            </span>
          </div>
          <div style={styles.cardMeta}>
            <span>{route.distDisplay}</span>
            <span>{route.steps.length} steps</span>
            <span>{Math.round(route.confidence * 100)}% conf</span>
          </div>
          <div style={styles.miniScores}>
            <MiniBar label="Safety" value={route.safety_score} />
            <MiniBar label="Crowd" value={1 - route.crowd_exposure} />
          </div>
        </button>
      ))}
    </div>
  );
}

function MiniBar({ label, value }: { label: string; value: number }) {
  const pct = Math.max(0, Math.min(100, value * 100));
  const color = value > 0.7 ? "#4caf50" : value > 0.4 ? "#ff9800" : "#f44336";
  return (
    <div style={styles.miniRow}>
      <span style={styles.miniLabel}>{label}</span>
      <div style={styles.miniTrack}>
        <div
          style={{ ...styles.miniFill, width: `${pct}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: "flex",
    gap: 8,
    overflowX: "auto",
    padding: "4px 0",
  },
  card: {
    flex: "0 0 180px",
    border: "1px solid #333",
    borderRadius: 8,
    padding: 10,
    cursor: "pointer",
    transition: "border-color 0.2s, background-color 0.2s",
    textAlign: "left",
  },
  cardHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 6,
  },
  grade: { fontSize: 22, fontWeight: 800 },
  time: { fontSize: 14, fontWeight: 600, color: "#e0e0e0" },
  cardMeta: {
    display: "flex",
    gap: 8,
    fontSize: 11,
    color: "#888",
    marginBottom: 8,
  },
  miniScores: { display: "flex", flexDirection: "column", gap: 4 },
  miniRow: { display: "flex", alignItems: "center", gap: 4 },
  miniLabel: { width: 36, fontSize: 9, color: "#888" },
  miniTrack: { flex: 1, height: 3, backgroundColor: "#2d2d2d", borderRadius: 2 },
  miniFill: { height: "100%", borderRadius: 2 },
};

export const RouteComparison = memo(RouteComparisonInner);
