/**
 * AlternativeDecisions - Comparison table of rejected alternatives.
 *
 * Shows intervention type, simulated risk reduction, confidence,
 * and rejection reason for each alternative considered by the AI.
 */

"use client";

import { memo } from "react";

interface AlternativeDecisionItem {
  intervention_type: string;
  confidence: number;
  rejection_reason: string;
  simulated_risk_reduction: number;
}

interface AlternativeDecisionsProps {
  alternatives: AlternativeDecisionItem[];
}

const TYPE_LABELS: Record<string, string> = {
  do_nothing: "Do Nothing",
  redirect_volunteers: "Redirect Volunteers",
  open_secondary_gate: "Open Secondary Gate",
  deploy_medical: "Deploy Medical",
  close_corridor: "Close Corridor",
  reverse_flow: "Reverse Flow",
  split_crowd: "Split Crowd",
  multilingual_announcement: "Multilingual Announcement",
  increase_security: "Increase Security",
  accessibility_priority_routing: "Accessibility Priority Routing",
};

function AlternativeDecisionsInner({ alternatives }: AlternativeDecisionsProps) {
  if (alternatives.length === 0) return null;

  return (
    <div
      role="region"
      aria-label="Alternative decisions"
      style={styles.container}
    >
      <h3 style={styles.title}>Alternatives Considered</h3>
      <div style={styles.tableWrapper}>
        <table style={styles.table} role="table">
          <thead>
            <tr>
              <th style={{ ...styles.th, textAlign: "left" }}>Intervention</th>
              <th style={styles.th}>Reduction</th>
              <th style={styles.th}>Confidence</th>
              <th style={{ ...styles.th, textAlign: "left" }}>Why Rejected</th>
            </tr>
          </thead>
          <tbody>
            {alternatives.map((alt, idx) => (
              <tr key={idx} style={styles.row}>
                <td style={{ ...styles.td, fontWeight: 500, color: "#e0e0e0" }}>
                  {TYPE_LABELS[alt.intervention_type] ?? alt.intervention_type}
                </td>
                <td style={{ ...styles.td, textAlign: "center" }}>
                  <span
                    style={{
                      ...styles.reductionBadge,
                      color: alt.simulated_risk_reduction > 0 ? "#4caf50" : "#9e9e9e",
                    }}
                  >
                    {alt.simulated_risk_reduction > 0 ? "+" : ""}
                    {(alt.simulated_risk_reduction * 100).toFixed(1)}%
                  </span>
                </td>
                <td style={{ ...styles.td, textAlign: "center" }}>
                  <span style={styles.confidenceValue}>
                    {(alt.confidence * 100).toFixed(0)}%
                  </span>
                </td>
                <td style={{ ...styles.td, color: "#9e9e9e", fontSize: 12 }}>
                  {alt.rejection_reason}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
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
  },
  title: {
    fontSize: 13,
    fontWeight: 600,
    color: "#e0e0e0",
    margin: 0,
    padding: "12px 16px",
    borderBottom: "1px solid #2d2d44",
  },
  tableWrapper: {
    overflowX: "auto",
  },
  table: {
    width: "100%",
    borderCollapse: "collapse",
    fontSize: 13,
  },
  th: {
    padding: "8px 12px",
    color: "#9e9e9e",
    fontSize: 11,
    fontWeight: 500,
    textTransform: "uppercase",
    letterSpacing: "0.5px",
    textAlign: "center",
    borderBottom: "1px solid #2d2d44",
  },
  row: {
    borderBottom: "1px solid #1f1f35",
  },
  td: {
    padding: "8px 12px",
    color: "#bdbdbd",
    verticalAlign: "top",
  },
  reductionBadge: {
    fontVariantNumeric: "tabular-nums",
    fontWeight: 500,
  },
  confidenceValue: {
    fontVariantNumeric: "tabular-nums",
    color: "#bdbdbd",
  },
};

export const AlternativeDecisions = memo(AlternativeDecisionsInner);
