/**
 * ConfidenceMeter - Circular confidence visualization.
 *
 * Shows overall confidence as a circular progress indicator with
 * optional breakdown of sub-scores (sensor agreement, historical
 * similarity, model agreement, data freshness).
 */

"use client";

import { memo, useMemo } from "react";

import type { ConfidenceBreakdown } from "@/types/ai-intelligence";

interface ConfidenceMeterProps {
  confidence: number;
  breakdown?: ConfidenceBreakdown;
  size?: "sm" | "md" | "lg";
}

const SIZE_CONFIG: Record<
  "sm" | "md" | "lg",
  { canvas: number; stroke: number; fontSize: number; labelSize: number }
> = {
  sm: { canvas: 48, stroke: 4, fontSize: 11, labelSize: 9 },
  md: { canvas: 80, stroke: 6, fontSize: 16, labelSize: 11 },
  lg: { canvas: 120, stroke: 8, fontSize: 24, labelSize: 12 },
};

function getConfidenceColor(value: number): string {
  if (value < 0.3) return "#f44336";
  if (value <= 0.6) return "#ff9800";
  return "#4caf50";
}

function ConfidenceMeterInner({
  confidence,
  breakdown,
  size = "md",
}: ConfidenceMeterProps) {
  const config = SIZE_CONFIG[size];
  const radius = (config.canvas - config.stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const clampedConfidence = Math.max(0, Math.min(1, confidence));
  const offset = circumference * (1 - clampedConfidence);
  const color = getConfidenceColor(clampedConfidence);
  const percentage = Math.round(clampedConfidence * 100);

  const breakdownEntries = useMemo(() => {
    if (!breakdown) return [];
    return [
      { label: "Sensor", value: breakdown.sensor_agreement },
      { label: "Historical", value: breakdown.historical_similarity },
      { label: "Model", value: breakdown.model_agreement },
      { label: "Freshness", value: breakdown.data_freshness },
    ];
  }, [breakdown]);

  return (
    <div
      role="meter"
      aria-label={`Confidence: ${percentage}%`}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={percentage}
      style={styles.wrapper}
    >
      <svg
        width={config.canvas}
        height={config.canvas}
        viewBox={`0 0 ${config.canvas} ${config.canvas}`}
        aria-hidden="true"
      >
        <circle
          cx={config.canvas / 2}
          cy={config.canvas / 2}
          r={radius}
          fill="none"
          stroke="#2d2d2d"
          strokeWidth={config.stroke}
        />
        <circle
          cx={config.canvas / 2}
          cy={config.canvas / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={config.stroke}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          style={{
            transform: "rotate(-90deg)",
            transformOrigin: "center",
            transition: "stroke-dashoffset 0.4s ease",
          }}
        />
        <text
          x="50%"
          y="50%"
          textAnchor="middle"
          dominantBaseline="central"
          fill="#ffffff"
          fontSize={config.fontSize}
          fontWeight={700}
          fontFamily="system-ui, sans-serif"
        >
          {percentage}%
        </text>
      </svg>

      {breakdownEntries.length > 0 && (
        <div style={styles.breakdown}>
          {breakdownEntries.map((entry) => (
            <div key={entry.label} style={styles.breakdownRow}>
              <span style={styles.breakdownLabel}>{entry.label}</span>
              <div style={styles.breakdownBarTrack}>
                <div
                  style={{
                    ...styles.breakdownBarFill,
                    width: `${Math.round(entry.value * 100)}%`,
                    backgroundColor: getConfidenceColor(entry.value),
                  }}
                />
              </div>
              <span style={styles.breakdownValue}>
                {Math.round(entry.value * 100)}%
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  wrapper: {
    display: "inline-flex",
    alignItems: "center",
    gap: 12,
  },
  breakdown: {
    display: "flex",
    flexDirection: "column",
    gap: 4,
  },
  breakdownRow: {
    display: "flex",
    alignItems: "center",
    gap: 6,
  },
  breakdownLabel: {
    fontSize: 11,
    color: "#9e9e9e",
    width: 64,
  },
  breakdownBarTrack: {
    width: 60,
    height: 4,
    backgroundColor: "#2d2d2d",
    borderRadius: 2,
    overflow: "hidden",
  },
  breakdownBarFill: {
    height: "100%",
    borderRadius: 2,
    transition: "width 0.3s ease",
  },
  breakdownValue: {
    fontSize: 11,
    color: "#bdbdbd",
    fontVariantNumeric: "tabular-nums",
    width: 30,
    textAlign: "right",
  },
};

export const ConfidenceMeter = memo(ConfidenceMeterInner);
