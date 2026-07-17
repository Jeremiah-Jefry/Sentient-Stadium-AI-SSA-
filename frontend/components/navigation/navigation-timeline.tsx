/**
 * NavigationTimeline - Vertical timeline showing route progress.
 * Displays completed steps, current position, and remaining steps
 * with estimated time remaining.
 */

"use client";

import { memo, useMemo } from "react";

import type { RouteStep } from "@/types/navigation";

interface NavigationTimelineProps {
  steps: RouteStep[];
  currentStepIndex: number;
  estimatedRemainingSeconds?: number;
}

function NavigationTimelineInner({
  steps,
  currentStepIndex,
  estimatedRemainingSeconds,
}: NavigationTimelineProps) {
  const remainingDisplay = useMemo(() => {
    if (estimatedRemainingSeconds === undefined) return null;
    const min = Math.floor(estimatedRemainingSeconds / 60);
    const sec = Math.round(estimatedRemainingSeconds % 60);
    return `${min}m ${sec}s remaining`;
  }, [estimatedRemainingSeconds]);

  return (
    <div style={styles.container} role="list" aria-label="Navigation timeline">
      {remainingDisplay && (
        <div style={styles.eta}>{remainingDisplay}</div>
      )}
      {steps.map((step, idx) => {
        const status =
          idx < currentStepIndex
            ? "completed"
            : idx === currentStepIndex
              ? "current"
              : "upcoming";
        return (
          <div
            key={step.node_id}
            style={{
              ...styles.step,
              opacity: status === "upcoming" ? 0.5 : 1,
            }}
            role="listitem"
            aria-current={status === "current" ? "step" : undefined}
          >
            <div style={styles.indicator}>
              <div
                style={{
                  ...styles.dot,
                  backgroundColor:
                    status === "completed"
                      ? "#4caf50"
                      : status === "current"
                        ? "#2196f3"
                        : "#555",
                }}
              />
              {idx < steps.length - 1 && <div style={styles.line} />}
            </div>
            <div style={styles.content}>
              <span style={styles.name}>
                {step.name || `Step ${idx + 1}`}
              </span>
              {step.edge_type && (
                <span style={styles.edge}>{step.edge_type}</span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: { padding: "4px 0" },
  eta: {
    fontSize: 12,
    fontWeight: 600,
    color: "#2196f3",
    marginBottom: 8,
    textAlign: "center",
  },
  step: { display: "flex", gap: 10, minHeight: 32 },
  indicator: { display: "flex", flexDirection: "column", alignItems: "center", width: 14 },
  dot: { width: 8, height: 8, borderRadius: "50%", marginTop: 4, flexShrink: 0 },
  line: { flex: 1, width: 2, backgroundColor: "#444", marginTop: 2 },
  content: { display: "flex", flexDirection: "column", gap: 1, paddingBottom: 4 },
  name: { fontSize: 12, fontWeight: 500, color: "#e0e0e0" },
  edge: { fontSize: 10, color: "#666", fontStyle: "italic" },
};

export const NavigationTimeline = memo(NavigationTimelineInner);
