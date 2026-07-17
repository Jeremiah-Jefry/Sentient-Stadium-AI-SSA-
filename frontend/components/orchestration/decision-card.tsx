/**
 * DecisionCard - Card displaying an orchestration decision.
 *
 * Shows decision summary, confidence badge, safety level,
 * agents involved, evidence/alternative counts, and expandable details.
 */

"use client";

import { memo, useCallback, useState } from "react";
import {
  ChevronDown,
  Users,
  FileText,
  Layers,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  AlertOctagon,
} from "lucide-react";

import type {
  OrchestratorResponse,
  SafetyLevel,
  ExecutionStatus,
} from "@/types/orchestration";

interface DecisionCardProps {
  decision: OrchestratorResponse;
  role?: "volunteer" | "admin" | "operator";
}

const SAFETY_CONFIG: Record<
  SafetyLevel,
  { label: string; color: string; icon: typeof AlertTriangle }
> = {
  safe: {
    label: "Safe",
    color: "text-emerald-400 bg-emerald-500/10 border-emerald-500/30",
    icon: CheckCircle2,
  },
  warning: {
    label: "Warning",
    color: "text-amber-400 bg-amber-500/10 border-amber-500/30",
    icon: AlertTriangle,
  },
  dangerous: {
    label: "Dangerous",
    color: "text-red-400 bg-red-500/10 border-red-500/30",
    icon: XCircle,
  },
  critical: {
    label: "Critical",
    color: "text-red-500 bg-red-500/10 border-red-500/30",
    icon: AlertOctagon,
  },
  requires_human_review: {
    label: "Human Review",
    color: "text-purple-400 bg-purple-500/10 border-purple-500/30",
    icon: AlertTriangle,
  },
};

const STATUS_COLORS: Record<ExecutionStatus, string> = {
  completed: "text-emerald-400",
  executing: "text-indigo-400",
  planning: "text-indigo-400",
  failed: "text-red-400",
  cancelled: "text-gray-400",
  timeout: "text-amber-400",
  pending: "text-gray-500",
  aggregating: "text-indigo-400",
  validating: "text-indigo-400",
};

function formatDuration(ms: number | null): string {
  if (ms === null) return "\u2014";
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function getConfidenceBadgeColor(confidence: number): string {
  if (confidence > 0.8) return "text-emerald-400 bg-emerald-500/10 border-emerald-500/30";
  if (confidence > 0.5) return "text-amber-400 bg-amber-500/10 border-amber-500/30";
  return "text-red-400 bg-red-500/10 border-red-500/30";
}

interface DetailSectionProps {
  decision: OrchestratorResponse;
}

function DecisionDetails({ decision }: DetailSectionProps) {
  const { confidence_report, safety_report, result } = decision;
  const metrics = [
    { label: "Agreement", value: confidence_report.agreement_score },
    { label: "Reasoning", value: confidence_report.reasoning_quality },
    { label: "Evidence", value: confidence_report.evidence_strength },
    { label: "Knowledge", value: confidence_report.knowledge_base_coverage },
  ];

  return (
    <div className="px-4 py-3 border-t border-gray-800 space-y-3">
      {confidence_report.limiting_factors.length > 0 && (
        <div>
          <h4 className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-1">
            Limiting Factors
          </h4>
          <ul className="space-y-0.5">
            {confidence_report.limiting_factors.map((f) => (
              <li key={f} className="text-[11px] text-amber-400 flex items-center gap-1.5">
                <AlertTriangle className="h-3 w-3 flex-shrink-0" />
                {f}
              </li>
            ))}
          </ul>
        </div>
      )}

      {safety_report.violations.length > 0 && (
        <div>
          <h4 className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-1">
            Safety Violations
          </h4>
          <ul className="space-y-0.5">
            {safety_report.violations.map((v) => (
              <li key={v} className="text-[11px] text-red-400 flex items-center gap-1.5">
                <XCircle className="h-3 w-3 flex-shrink-0" />
                {v}
              </li>
            ))}
          </ul>
        </div>
      )}

      {result && (
        <div>
          <h4 className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-1">
            Result
          </h4>
          <pre className="text-[10px] text-gray-400 bg-gray-800/50 rounded p-2 overflow-x-auto font-mono">
            {JSON.stringify(result, null, 2)}
          </pre>
        </div>
      )}

      <div className="grid grid-cols-2 gap-2 text-[10px]">
        {metrics.map((m) => (
          <div key={m.label} className="bg-gray-800/50 rounded p-2">
            <span className="text-gray-500">{m.label}</span>
            <p className="text-gray-300 font-semibold">
              {Math.round(m.value * 100)}%
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

function DecisionCardInner({ decision, role = "volunteer" }: DecisionCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const toggle = useCallback(() => setIsExpanded((prev) => !prev), []);

  const safetyConfig = SAFETY_CONFIG[decision.safety_report.level];
  const SafetyIcon = safetyConfig.icon;
  const confidencePercent = Math.round(decision.confidence_report.overall * 100);
  const showDetailed = role === "admin" || role === "operator";

  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900/50 overflow-hidden transition-colors hover:border-gray-700">
      <div className="px-4 py-3">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs font-semibold text-gray-200 uppercase tracking-wider">
                {decision.intent.replace(/_/g, " ")}
              </span>
              <span className={`text-[10px] font-mono ${STATUS_COLORS[decision.status]}`}>
                {decision.status}
              </span>
            </div>
            <p className="text-xs text-gray-400 mt-1">
              {decision.request_type.replace(/_/g, " ")}
              {decision.duration_ms !== null && (
                <span className="ml-2 text-gray-500 font-mono tabular-nums">
                  {formatDuration(decision.duration_ms)}
                </span>
              )}
            </p>
          </div>

          <div className="flex items-center gap-2 flex-shrink-0">
            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold border ${getConfidenceBadgeColor(decision.confidence_report.overall)}`}>
              {confidencePercent}%
            </span>
            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold border ${safetyConfig.color}`}>
              <SafetyIcon className="h-3 w-3" />
              {safetyConfig.label}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-4 mt-2 text-[10px] text-gray-500">
          <span className="flex items-center gap-1">
            <Users className="h-3 w-3" />
            {decision.agents_involved.length} agents
          </span>
          <span className="flex items-center gap-1">
            <FileText className="h-3 w-3" />
            {decision.reasoning_chain.stages.length} stages
          </span>
          <span className="flex items-center gap-1">
            <Layers className="h-3 w-3" />
            {decision.execution_plan.total_steps} steps
          </span>
          <span className="font-mono tabular-nums ml-auto">
            {decision.execution_id.slice(0, 8)}
          </span>
        </div>
      </div>

      <button
        type="button"
        onClick={toggle}
        aria-expanded={isExpanded}
        className="w-full flex items-center justify-center gap-1 px-4 py-1.5 bg-gray-800/50 border-t border-gray-800 text-[10px] text-gray-400 hover:text-gray-300 hover:bg-gray-800 transition-colors cursor-pointer"
      >
        {isExpanded ? "Collapse" : "Expand"} details
        <ChevronDown className={`h-3 w-3 transition-transform duration-200 ${isExpanded ? "rotate-180" : ""}`} />
      </button>

      {isExpanded && showDetailed && <DecisionDetails decision={decision} />}
    </div>
  );
}

export const DecisionCard = memo(DecisionCardInner);
