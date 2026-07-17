/**
 * PredictionCard - Compact card showing a single AI prediction.
 *
 * Displays prediction type, predicted value, confidence, time window,
 * contributing factors, and evidence count. Suitable for dashboard grids.
 */

"use client";

import { memo, useMemo } from "react";

import { ConfidenceMeter } from "./confidence-meter";
import type { PredictionResponse, PredictionType } from "@/types/ai-intelligence";

interface PredictionCardProps {
  prediction: PredictionResponse;
}

const PREDICTION_TYPE_LABELS: Record<PredictionType, string> = {
  bottleneck: "Bottleneck",
  congestion: "Congestion",
  queue_growth: "Queue Growth",
  dangerous_density: "Dangerous Density",
  medical_overload: "Medical Overload",
  volunteer_shortage: "Volunteer Shortage",
  exit_saturation: "Exit Saturation",
  transport_congestion: "Transport Congestion",
  wheelchair_blockage: "Wheelchair Blockage",
  lost_child: "Lost Child",
  cleaning_overload: "Cleaning Overload",
  security_pressure: "Security Pressure",
};

function PredictionCardInner({ prediction }: PredictionCardProps) {
  const typeLabel = PREDICTION_TYPE_LABELS[prediction.prediction_type];
  const windowMinutes = Math.round(
    prediction.prediction_window_seconds / 60,
  );
  const topFactors = useMemo(
    () => prediction.contributing_factors.slice(0, 3),
    [prediction.contributing_factors],
  );

  const isExpired = new Date(prediction.valid_until) < new Date();

  return (
    <article
      aria-label={`Prediction: ${typeLabel}`}
      style={styles.card}
    >
      <div style={styles.header}>
        <span style={styles.typeLabel}>{typeLabel}</span>
        {isExpired && <span style={styles.expiredBadge}>Expired</span>}
      </div>

      <div style={styles.valueRow}>
        <span style={styles.value}>{prediction.predicted_value.toFixed(1)}</span>
        <ConfidenceMeter
          confidence={prediction.confidence}
          size="sm"
        />
      </div>

      <div style={styles.meta}>
        <span style={styles.metaItem}>
          Window: {windowMinutes}m
        </span>
        <span style={styles.metaItem}>
          Evidence: {prediction.evidence_events.length}
        </span>
      </div>

      {topFactors.length > 0 && (
        <div style={styles.factors}>
          <span style={styles.factorsLabel}>Contributing factors</span>
          <ul style={styles.factorList}>
            {topFactors.map((f, idx) => (
              <li key={idx} style={styles.factorItem}>
                <span style={styles.factorName}>{f.factor}</span>
                <span style={styles.factorWeight}>
                  {(f.weight * 100).toFixed(0)}%
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div style={styles.footer}>
        <span style={styles.modelVersion}>v{prediction.model_version}</span>
        <time style={styles.timestamp} dateTime={prediction.predicted_at}>
          {new Date(prediction.predicted_at).toLocaleTimeString()}
        </time>
      </div>
    </article>
  );
}

const styles: Record<string, React.CSSProperties> = {
  card: {
    backgroundColor: "#1a1a2e",
    border: "1px solid #2d2d44",
    borderRadius: 8,
    padding: 16,
    display: "flex",
    flexDirection: "column",
    gap: 10,
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  typeLabel: {
    fontSize: 14,
    fontWeight: 600,
    color: "#e0e0e0",
  },
  expiredBadge: {
    fontSize: 11,
    fontWeight: 500,
    color: "#f44336",
    backgroundColor: "rgba(244, 67, 54, 0.12)",
    padding: "2px 6px",
    borderRadius: 4,
  },
  valueRow: {
    display: "flex",
    alignItems: "center",
    gap: 12,
  },
  value: {
    fontSize: 24,
    fontWeight: 700,
    color: "#ffffff",
    fontVariantNumeric: "tabular-nums",
  },
  meta: {
    display: "flex",
    gap: 12,
  },
  metaItem: {
    fontSize: 12,
    color: "#9e9e9e",
  },
  factors: {
    display: "flex",
    flexDirection: "column",
    gap: 4,
  },
  factorsLabel: {
    fontSize: 11,
    fontWeight: 500,
    color: "#757575",
    textTransform: "uppercase",
    letterSpacing: "0.5px",
  },
  factorList: {
    listStyle: "none",
    margin: 0,
    padding: 0,
  },
  factorItem: {
    display: "flex",
    justifyContent: "space-between",
    fontSize: 12,
    color: "#bdbdbd",
    padding: "2px 0",
  },
  factorName: {
    textTransform: "capitalize",
  },
  factorWeight: {
    fontVariantNumeric: "tabular-nums",
    color: "#9e9e9e",
  },
  footer: {
    display: "flex",
    justifyContent: "space-between",
    borderTop: "1px solid #2d2d44",
    paddingTop: 8,
    marginTop: 4,
  },
  modelVersion: {
    fontSize: 11,
    color: "#757575",
  },
  timestamp: {
    fontSize: 11,
    color: "#757575",
  },
};

export const PredictionCard = memo(PredictionCardInner);
