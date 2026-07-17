/**
 * InterventionSimulator - Interactive what-if simulation tool.
 *
 * Allows selecting an intervention type, configuring dynamic parameters,
 * running simulation, and displaying results with risk before/after.
 */

"use client";

import { memo, useCallback, useMemo, useState } from "react";

import { RiskGauge } from "./risk-gauge";
import type {
  InterventionType,
  RiskLevel,
  SimulatedInterventionResponse,
} from "@/types/ai-intelligence";

interface InterventionSimulatorProps {
  venueId: string;
  onSimulate: (
    venueId: string,
    type: string,
    params: Record<string, unknown>,
  ) => Promise<SimulatedInterventionResponse | null>;
}

interface ParamDef {
  key: string;
  label: string;
  type: "number" | "string";
  default: string;
}

interface InterventionOption {
  value: InterventionType;
  label: string;
  params: ParamDef[];
}

const INTERVENTION_OPTIONS: InterventionOption[] = [
  { value: "do_nothing", label: "Do Nothing", params: [] },
  {
    value: "redirect_volunteers",
    label: "Redirect Volunteers",
    params: [
      { key: "target_zone_id", label: "Target Zone ID", type: "string", default: "" },
      { key: "volunteer_count", label: "Volunteer Count", type: "number", default: "3" },
    ],
  },
  {
    value: "open_secondary_gate",
    label: "Open Secondary Gate",
    params: [{ key: "gate_id", label: "Gate ID", type: "string", default: "" }],
  },
  {
    value: "deploy_medical",
    label: "Deploy Medical",
    params: [
      { key: "medical_team_id", label: "Medical Team ID", type: "string", default: "" },
      { key: "priority", label: "Priority (1-5)", type: "number", default: "3" },
    ],
  },
  {
    value: "close_corridor",
    label: "Close Corridor",
    params: [{ key: "corridor_id", label: "Corridor ID", type: "string", default: "" }],
  },
  { value: "reverse_flow", label: "Reverse Flow", params: [] },
  { value: "split_crowd", label: "Split Crowd", params: [] },
  {
    value: "multilingual_announcement",
    label: "Multilingual Announcement",
    params: [
      { key: "message_key", label: "Message Key", type: "string", default: "" },
      { key: "languages", label: "Languages (comma-sep)", type: "string", default: "en,es,fr" },
    ],
  },
  {
    value: "increase_security",
    label: "Increase Security",
    params: [{ key: "additional_officers", label: "Additional Officers", type: "number", default: "2" }],
  },
  { value: "accessibility_priority_routing", label: "Accessibility Priority Routing", params: [] },
];

const selectStyle: React.CSSProperties = {
  backgroundColor: "#16162a", border: "1px solid #2d2d44", borderRadius: 6,
  padding: "8px 12px", color: "#e0e0e0", fontSize: 13, outline: "none", width: "100%",
};

const inputStyle: React.CSSProperties = { ...selectStyle };

function InterventionSimulatorInner({ venueId, onSimulate }: InterventionSimulatorProps) {
  const [selectedType, setSelectedType] = useState<InterventionType>("do_nothing");
  const [paramValues, setParamValues] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SimulatedInterventionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const selectedOption = useMemo(
    () => INTERVENTION_OPTIONS.find((opt) => opt.value === selectedType),
    [selectedType],
  );

  const handleTypeChange = useCallback((e: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedType(e.target.value as InterventionType);
    setParamValues({});
    setResult(null);
  }, []);

  const handleParamChange = useCallback((key: string, value: string) => {
    setParamValues((prev) => ({ ...prev, [key]: value }));
  }, []);

  const handleSimulate = useCallback(async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    const params: Record<string, unknown> = {};
    if (selectedOption) {
      for (const param of selectedOption.params) {
        const raw = paramValues[param.key] ?? param.default;
        params[param.key] = param.type === "number" ? Number(raw) : raw;
      }
    }
    try {
      setResult(await onSimulate(venueId, selectedType, params));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Simulation failed");
    } finally {
      setLoading(false);
    }
  }, [venueId, selectedType, selectedOption, paramValues, onSimulate]);

  return (
    <div role="region" aria-label="Intervention simulator" style={{ backgroundColor: "#1a1a2e", border: "1px solid #2d2d44", borderRadius: 8, overflow: "hidden" }}>
      <h3 style={{ fontSize: 14, fontWeight: 600, color: "#e0e0e0", margin: 0, padding: "12px 16px", borderBottom: "1px solid #2d2d44" }}>Intervention Simulator</h3>

      <div style={{ padding: 16, display: "flex", flexDirection: "column", gap: 10 }}>
        <label style={{ fontSize: 12, fontWeight: 500, color: "#9e9e9e", textTransform: "uppercase", letterSpacing: "0.5px" }} htmlFor="intervention-type">Intervention Type</label>
        <select id="intervention-type" value={selectedType} onChange={handleTypeChange} style={selectStyle}>
          {INTERVENTION_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>

        {selectedOption?.params.map((param) => (
          <div key={param.key}>
            <label style={{ fontSize: 12, fontWeight: 500, color: "#9e9e9e", textTransform: "uppercase", letterSpacing: "0.5px" }} htmlFor={`param-${param.key}`}>{param.label}</label>
            <input id={`param-${param.key}`} type={param.type} value={paramValues[param.key] ?? param.default} onChange={(e) => handleParamChange(param.key, e.target.value)} style={inputStyle} />
          </div>
        ))}

        <button
          type="button"
          onClick={handleSimulate}
          disabled={loading}
          style={{ backgroundColor: loading ? "#1565c066" : "#1565c0", border: "none", borderRadius: 6, padding: "10px 24px", color: "#ffffff", fontSize: 14, fontWeight: 600, cursor: loading ? "not-allowed" : "pointer", width: "100%" }}
          aria-busy={loading}
        >
          {loading ? "Simulating..." : "Simulate"}
        </button>
      </div>

      {error && (
        <div role="alert" style={{ margin: "0 16px", padding: 10, backgroundColor: "rgba(244, 67, 54, 0.12)", color: "#f44336", borderRadius: 6, fontSize: 13 }}>{error}</div>
      )}

      {result && (
        <div style={{ padding: 16, borderTop: "1px solid #2d2d44", display: "flex", flexDirection: "column", gap: 12 }}>
          <h4 style={{ fontSize: 13, fontWeight: 600, color: "#e0e0e0", margin: 0 }}>Simulation Results</h4>
          <div style={{ display: "flex", gap: 16 }}>
            <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 4 }}>
              <span style={{ fontSize: 11, fontWeight: 500, color: "#9e9e9e", textTransform: "uppercase" }}>Before</span>
              <RiskGauge level={result.risk_before as RiskLevel} score={100} />
            </div>
            <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 4 }}>
              <span style={{ fontSize: 11, fontWeight: 500, color: "#9e9e9e", textTransform: "uppercase" }}>After</span>
              <RiskGauge level={result.risk_after as RiskLevel} score={100 - result.simulated_risk_reduction * 100} />
            </div>
          </div>
          <div style={{ display: "flex", gap: 12 }}>
            <div style={{ flex: 1, backgroundColor: "#16162a", borderRadius: 6, padding: "8px 12px", display: "flex", flexDirection: "column", gap: 4 }}>
              <span style={{ fontSize: 11, color: "#9e9e9e" }}>Risk Reduction</span>
              <span style={{ fontSize: 20, fontWeight: 700, color: "#ffffff", fontVariantNumeric: "tabular-nums" }}>{(result.simulated_risk_reduction * 100).toFixed(1)}%</span>
            </div>
            <div style={{ flex: 1, backgroundColor: "#16162a", borderRadius: 6, padding: "8px 12px", display: "flex", flexDirection: "column", gap: 4 }}>
              <span style={{ fontSize: 11, color: "#9e9e9e" }}>Confidence</span>
              <span style={{ fontSize: 20, fontWeight: 700, color: "#ffffff", fontVariantNumeric: "tabular-nums" }}>{(result.simulated_confidence * 100).toFixed(0)}%</span>
            </div>
          </div>
          {result.evaluation_factors.length > 0 && (
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <span style={{ fontSize: 11, fontWeight: 500, color: "#9e9e9e", textTransform: "uppercase" }}>Evaluation Factors</span>
              {result.evaluation_factors.map((f, idx) => (
                <div key={idx} style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: "#bdbdbd", padding: "2px 0" }}>
                  <span style={{ textTransform: "capitalize" }}>{f.factor}</span>
                  <span style={{ fontVariantNumeric: "tabular-nums" }}>{f.value.toFixed(3)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export const InterventionSimulator = memo(InterventionSimulatorInner);
