/**
 * LiveRerouteAlert - Notification banner for active route replanning.
 * Displays when a route is being recalculated due to changing conditions.
 */

"use client";

import { memo } from "react";

interface LiveRerouteAlertProps {
  trigger: string;
  reason: string;
  newTimeSeconds?: number;
  onDismiss?: () => void;
}

const TRIGGER_LABELS: Record<string, string> = {
  gate_closure: "Gate Closure",
  crowd_surge: "Crowd Surge",
  medical_incident: "Medical Incident",
  weather_change: "Weather Change",
  security_restriction: "Security Alert",
  infrastructure_failure: "Infrastructure Issue",
  escalator_down: "Escalator Down",
  elevator_down: "Elevator Down",
  emergency_declared: "Emergency",
};

function LiveRerouteAlertInner({
  trigger,
  reason,
  newTimeSeconds,
  onDismiss,
}: LiveRerouteAlertProps) {
  const label = TRIGGER_LABELS[trigger] ?? trigger;
  const newTime = newTimeSeconds
    ? `${Math.floor(newTimeSeconds / 60)}m ${Math.round(newTimeSeconds % 60)}s`
    : null;

  return (
    <div
      style={styles.container}
      role="alert"
      aria-live="assertive"
      aria-label={`Route updated: ${label}`}
    >
      <div style={styles.icon}>!</div>
      <div style={styles.content}>
        <span style={styles.title}>Route Updated</span>
        <span style={styles.reason}>
          {label}: {reason}
        </span>
        {newTime && (
          <span style={styles.newTime}>New ETA: {newTime}</span>
        )}
      </div>
      {onDismiss && (
        <button
          type="button"
          style={styles.dismiss}
          onClick={onDismiss}
          aria-label="Dismiss alert"
        >
          X
        </button>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    padding: "10px 14px",
    backgroundColor: "#3e2723",
    border: "1px solid #ff9800",
    borderRadius: 8,
    marginBottom: 8,
  },
  icon: {
    width: 28,
    height: 28,
    borderRadius: "50%",
    backgroundColor: "#ff9800",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 14,
    fontWeight: 800,
    color: "#000",
    flexShrink: 0,
  },
  content: { flex: 1, display: "flex", flexDirection: "column", gap: 2 },
  title: { fontSize: 12, fontWeight: 700, color: "#ff9800" },
  reason: { fontSize: 12, color: "#ccc" },
  newTime: { fontSize: 11, color: "#aaa" },
  dismiss: {
    background: "none",
    border: "none",
    color: "#888",
    cursor: "pointer",
    fontSize: 14,
    padding: 4,
  },
};

export const LiveRerouteAlert = memo(LiveRerouteAlertInner);
