/**
 * RouteExplanation - Panel displaying why a route was selected.
 * Shows reasoning, risk factors, bottlenecks, accessibility notes,
 * and tradeoffs in a structured, scannable format.
 */

"use client";

import { memo } from "react";

import type { RouteExplanation as RouteExplanationType } from "@/types/navigation";

interface RouteExplanationProps {
  explanation: RouteExplanationType;
}

function RouteExplanationInner({ explanation }: RouteExplanationProps) {
  return (
    <div style={styles.container} role="region" aria-label="Route explanation">
      <p style={styles.summary}>{explanation.summary}</p>

      <Section title="Why Selected" items={[explanation.why_selected]} />
      <Section title="Risk Factors" items={explanation.risk_factors} />
      <Section title="Expected Bottlenecks" items={explanation.expected_bottlenecks} />
      <Section title="Predicted Delays" items={explanation.predicted_delays} />
      <Section title="Accessibility" items={explanation.accessibility_notes} />
      <Section title="Tradeoffs" items={explanation.tradeoffs} />
      <Section title="Why Alternatives Rejected" items={explanation.why_rejected_alternatives} />
    </div>
  );
}

function Section({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <div style={styles.section}>
      <h4 style={styles.sectionTitle}>{title}</h4>
      <ul style={styles.list}>
        {items.map((item, idx) => (
          <li key={idx} style={styles.listItem}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: { padding: 12 },
  summary: {
    fontSize: 14,
    fontWeight: 600,
    color: "#e0e0e0",
    marginBottom: 12,
    lineHeight: 1.4,
  },
  section: { marginBottom: 10 },
  sectionTitle: {
    fontSize: 11,
    fontWeight: 600,
    color: "#888",
    textTransform: "uppercase",
    letterSpacing: 0.5,
    marginBottom: 4,
  },
  list: { listStyle: "none", padding: 0, margin: 0 },
  listItem: {
    fontSize: 12,
    color: "#bbb",
    padding: "2px 0",
    lineHeight: 1.4,
  },
};

export const RouteExplanationPanel = memo(RouteExplanationInner);
