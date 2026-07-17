/**
 * RiskGauge - Horizontal gauge bar displaying risk level and score.
 *
 * Color-coded by risk level with ARIA labels for screen readers
 * and keyboard focusable for accessibility.
 */

"use client";

import { memo, useMemo } from "react";

import type { RiskLevel } from "@/types/ai-intelligence";

interface RiskGaugeProps {
  level: RiskLevel;
  score: number;
  label?: string;
}

const RISK_COLORS: Record<RiskLevel, string> = {
  green: "#4caf50",
  yellow: "#ff9800",
  orange: "#ff5722",
  red: "#f44336",
  critical: "#9c27b0",
};

const RISK_LABELS: Record<RiskLevel, string> = {
  green: "Green",
  yellow: "Yellow",
  orange: "Orange",
  red: "Red",
  critical: "Critical",
};

const MAX_SCORE = 100;

function RiskGaugeInner({ level, score, label }: RiskGaugeProps) {
  const clampedScore = useMemo(
    () => Math.max(0, Math.min(MAX_SCORE, score)),
    [score],
  );

  const color = RISK_COLORS[level];
  const pct = (clampedScore / MAX_SCORE) * 100;
  const displayLabel = label ?? RISK_LABELS[level];

  const ariaLabel = `Risk level: ${displayLabel}. Score: ${clampedScore} out of ${MAX_SCORE}.`;

  return (
    <div
      role="meter"
      aria-label={ariaLabel}
      aria-valuemin={0}
      aria-valuemax={MAX_SCORE}
      aria-valuenow={clampedScore}
      aria-valuetext={`${displayLabel} - ${clampedScore}`}
      tabIndex={0}
      style={styles.container}
    >
      <div style={styles.header}>
        <span style={styles.label}>{displayLabel}</span>
        <span style={{ ...styles.score, color }}>{clampedScore}</span>
      </div>
      <div style={styles.track} role="presentation">
        <div
          style={{
            ...styles.fill,
            width: `${pct}%`,
            backgroundColor: color,
          }}
        />
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    width: "100%",
    outline: "none",
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 4,
  },
  label: {
    fontSize: 13,
    fontWeight: 500,
    color: "#e0e0e0",
  },
  score: {
    fontSize: 14,
    fontWeight: 700,
    fontVariantNumeric: "tabular-nums",
  },
  track: {
    width: "100%",
    height: 8,
    backgroundColor: "#2d2d2d",
    borderRadius: 4,
    overflow: "hidden",
  },
  fill: {
    height: "100%",
    borderRadius: 4,
    transition: "width 0.4s ease, background-color 0.4s ease",
  },
};

export const RiskGauge = memo(RiskGaugeInner);
