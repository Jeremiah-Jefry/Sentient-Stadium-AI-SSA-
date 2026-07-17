/**
 * ReasoningPanel - Explainable AI reasoning display.
 *
 * Shows summary, detailed reason, evidence, contributing factors,
 * alternatives, tradeoffs, and expected outcome in collapsible sections.
 */

"use client";

import { memo, useCallback, useState } from "react";

import type { ExplanationResponse } from "@/types/ai-intelligence";

interface ReasoningPanelProps {
  explanation: ExplanationResponse;
}

interface CollapsibleSectionProps {
  title: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}

function CollapsibleSection({ title, defaultOpen = false, children }: CollapsibleSectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  const toggle = useCallback(() => setIsOpen((prev) => !prev), []);

  return (
    <section style={{ borderBottom: "1px solid #2d2d44" }}>
      <button
        type="button"
        onClick={toggle}
        aria-expanded={isOpen}
        style={{ width: "100%", display: "flex", alignItems: "center", gap: 8, padding: "12px 16px", backgroundColor: "transparent", border: "none", color: "#e0e0e0", fontSize: 13, fontWeight: 600, cursor: "pointer", textAlign: "left" }}
      >
        <span style={{ fontSize: 10, color: "#9e9e9e", width: 12 }}>{isOpen ? "\u25BC" : "\u25B6"}</span>
        {title}
      </button>
      {isOpen && <div style={{ padding: "0 16px 12px" }}>{children}</div>}
    </section>
  );
}

const listStyle: React.CSSProperties = { listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: 6 };
const itemBg: React.CSSProperties = { backgroundColor: "#16162a", borderRadius: 4 };

function ReasoningPanelInner({ explanation }: ReasoningPanelProps) {
  return (
    <div role="region" aria-label="Decision explanation" style={{ backgroundColor: "#1a1a2e", border: "1px solid #2d2d44", borderRadius: 8, overflow: "hidden" }}>
      <CollapsibleSection title="Summary" defaultOpen>
        <p style={{ fontSize: 14, color: "#e0e0e0", lineHeight: 1.5, margin: 0 }}>{explanation.summary}</p>
      </CollapsibleSection>

      <CollapsibleSection title="Reasoning" defaultOpen>
        <p style={{ fontSize: 13, color: "#bdbdbd", lineHeight: 1.5, margin: 0 }}>{explanation.reason}</p>
      </CollapsibleSection>

      {explanation.evidence.length > 0 && (
        <CollapsibleSection title={`Evidence (${explanation.evidence.length})`}>
          <ul style={listStyle}>
            {explanation.evidence.map((item, idx) => (
              <li key={idx} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, color: "#bdbdbd", padding: "4px 8px", ...itemBg }}>
                <span style={{ fontWeight: 500, color: "#90caf9" }}>{item.event_type}</span>
                <span style={{ color: "#9e9e9e" }}>{item.source}</span>
                <time style={{ color: "#757575", marginLeft: "auto", fontVariantNumeric: "tabular-nums" }} dateTime={item.timestamp}>
                  {new Date(item.timestamp).toLocaleTimeString()}
                </time>
                {item.description && <span style={{ color: "#9e9e9e", fontSize: 11 }}>{item.description}</span>}
              </li>
            ))}
          </ul>
        </CollapsibleSection>
      )}

      {explanation.contributing_factors.length > 0 && (
        <CollapsibleSection title="Contributing Factors" defaultOpen>
          <ol style={{ margin: 0, padding: 0, listStyleType: "decimal", paddingLeft: 20 }}>
            {explanation.contributing_factors.map((factor, idx) => (
              <li key={idx} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 13, color: "#bdbdbd", padding: "4px 0" }}>
                <span style={{ textTransform: "capitalize" }}>{factor.factor}</span>
                <span style={{ fontVariantNumeric: "tabular-nums", color: "#9e9e9e" }}>{(factor.weight * 100).toFixed(0)}%</span>
              </li>
            ))}
          </ol>
        </CollapsibleSection>
      )}

      {explanation.alternatives.length > 0 && (
        <CollapsibleSection title="Alternatives Considered">
          <ul style={listStyle}>
            {explanation.alternatives.map((alt, idx) => (
              <li key={idx} style={{ display: "flex", flexDirection: "column", gap: 2, fontSize: 12, padding: "6px 8px", ...itemBg }}>
                <span style={{ fontWeight: 500, color: "#e0e0e0", textTransform: "capitalize" }}>{alt.intervention_type}</span>
                <span style={{ color: "#9e9e9e", fontSize: 11 }}>Rejected: {alt.rejection_reason}</span>
              </li>
            ))}
          </ul>
        </CollapsibleSection>
      )}

      {explanation.tradeoffs.length > 0 && (
        <CollapsibleSection title="Tradeoffs">
          <ul style={listStyle}>
            {explanation.tradeoffs.map((tradeoff, idx) => (
              <li key={idx} style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 12, padding: "6px 8px", ...itemBg }}>
                <span style={{ fontWeight: 600, color: "#e0e0e0", textTransform: "capitalize" }}>{tradeoff.factor}</span>
                <div style={{ display: "flex", flexDirection: "column", gap: 2, paddingLeft: 8 }}>
                  <span style={{ color: "#4caf50", fontSize: 11 }}>+ {tradeoff.pros}</span>
                  <span style={{ color: "#f44336", fontSize: 11 }}>&minus; {tradeoff.cons}</span>
                </div>
              </li>
            ))}
          </ul>
        </CollapsibleSection>
      )}

      <CollapsibleSection title="Expected Outcome" defaultOpen>
        <p style={{ fontSize: 13, color: "#bdbdbd", lineHeight: 1.5, margin: 0 }}>{explanation.expected_outcome}</p>
      </CollapsibleSection>
    </div>
  );
}

export const ReasoningPanel = memo(ReasoningPanelInner);
