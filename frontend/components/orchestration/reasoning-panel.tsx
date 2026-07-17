/**
 * ReasoningPanel - Multi-stage reasoning chain visualization.
 *
 * Shows the 8-stage pipeline (Observe → Think → Plan → Execute → Critique → Improve → Validate → Explain)
 * with expandable details, confidence, evidence, and duration per stage.
 */

"use client";

import { memo, useCallback, useState } from "react";
import { ChevronDown, Clock, Target, FileText } from "lucide-react";

import type {
  ReasoningChain,
  ReasoningStageResult,
  ExecutionStatus,
} from "@/types/orchestration";

interface ReasoningPanelProps {
  chain: ReasoningChain;
}

const STAGE_LABELS: Record<string, string> = {
  observe: "Observe",
  think: "Think",
  plan: "Plan",
  execute: "Execute",
  critique: "Critique",
  improve: "Improve",
  validate: "Validate",
  explain: "Explain",
};

const STAGE_ICONS: Record<string, string> = {
  observe: "\uD83D\uDC41",
  think: "\uD83E\uDDE0",
  plan: "\uD83D\uDCCB",
  execute: "\u26A1",
  critique: "\uD83D\uDD0D",
  improve: "\u2B06\uFE0F",
  validate: "\u2705",
  explain: "\uD83D\uDCA1",
};

function formatDuration(ms: number | null): string {
  if (ms === null) return "—";
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function getStatusColor(status: ExecutionStatus): string {
  switch (status) {
    case "completed":
      return "text-emerald-400 bg-emerald-500/10 border-emerald-500/30";
    case "executing":
    case "planning":
      return "text-indigo-400 bg-indigo-500/10 border-indigo-500/30";
    case "failed":
      return "text-red-400 bg-red-500/10 border-red-500/30";
    default:
      return "text-gray-500 bg-gray-800/50 border-gray-700";
  }
}

function getBarColor(confidence: number): string {
  if (confidence > 0.8) return "bg-emerald-500";
  if (confidence > 0.5) return "bg-amber-500";
  return "bg-red-500";
}

interface StageCardProps {
  result: ReasoningStageResult;
  isLast: boolean;
}

function StageCard({ result, isLast }: StageCardProps) {
  const [isOpen, setIsOpen] = useState(false);
  const toggle = useCallback(() => setIsOpen((prev) => !prev), []);

  const confidencePercent = Math.round(result.confidence * 100);

  return (
    <div className="relative">
      {!isLast && (
        <div className="absolute left-5 top-10 w-0.5 h-full bg-gray-700 -mb-2" />
      )}

      <div
        className={`relative flex gap-3 p-3 rounded-lg border transition-colors duration-200 ${getStatusColor(
          result.status,
        )} ${isOpen ? "bg-opacity-20" : ""}`}
      >
        <div className="flex-shrink-0 flex items-center justify-center w-8 h-8 rounded-full bg-gray-800 border border-gray-700 text-sm">
          {STAGE_ICONS[result.stage] ?? "?"}
        </div>

        <div className="flex-1 min-w-0">
          <button
            type="button"
            onClick={toggle}
            aria-expanded={isOpen}
            className="w-full flex items-center justify-between gap-2 text-left bg-transparent border-none p-0 cursor-pointer"
          >
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-gray-200">
                {STAGE_LABELS[result.stage] ?? result.stage}
              </span>
              <span className="text-[10px] uppercase tracking-wider text-gray-500">
                {result.status}
              </span>
            </div>
            <div className="flex items-center gap-2">
              {result.duration_ms !== null && (
                <span className="flex items-center gap-1 text-[10px] text-gray-500 font-mono tabular-nums">
                  <Clock className="h-3 w-3" />
                  {formatDuration(result.duration_ms)}
                </span>
              )}
              <ChevronDown
                className={`h-4 w-4 text-gray-500 transition-transform duration-200 ${
                  isOpen ? "rotate-180" : ""
                }`}
              />
            </div>
          </button>

          <div className="flex items-center gap-2 mt-1.5">
            <Target className="h-3 w-3 text-gray-500 flex-shrink-0" />
            <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-500 ${getBarColor(
                  result.confidence,
                )}`}
                style={{ width: `${confidencePercent}%` }}
              />
            </div>
            <span className="text-[10px] text-gray-400 font-mono tabular-nums w-8 text-right">
              {confidencePercent}%
            </span>
          </div>

          {isOpen && (
            <div className="mt-3 space-y-2 border-t border-gray-700/50 pt-2">
              {result.evidence.length > 0 && (
                <div>
                  <div className="flex items-center gap-1 mb-1">
                    <FileText className="h-3 w-3 text-gray-500" />
                    <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">
                      Evidence ({result.evidence.length})
                    </span>
                  </div>
                  <ul className="space-y-1">
                    {result.evidence.map((item, idx) => (
                      <li
                        key={idx}
                        className="text-[11px] text-gray-400 pl-4 relative before:content-[''] before:absolute before:left-1 before:top-1.5 before:w-1 before:h-1 before:rounded-full before:bg-gray-600"
                      >
                        <span className="text-gray-300 font-medium">
                          {item.type}
                        </span>
                        {" — "}
                        {item.content}
                        <span className="text-gray-600 ml-1">
                          (w: {item.weight.toFixed(2)})
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {Object.keys(result.output).length > 0 && (
                <div>
                  <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">
                    Output
                  </span>
                  <pre className="mt-1 text-[10px] text-gray-400 bg-gray-800/50 rounded p-2 overflow-x-auto font-mono">
                    {JSON.stringify(result.output, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function ReasoningPanelInner({ chain }: ReasoningPanelProps) {
  return (
    <div
      role="region"
      aria-label="Reasoning chain"
      className="rounded-lg border border-gray-800 bg-gray-900/50 overflow-hidden"
    >
      <div className="px-4 py-3 border-b border-gray-800 bg-gray-900">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-200">
            Reasoning Chain
          </h3>
          <span className="text-[10px] text-gray-500 font-mono">
            {chain.stages.length} stages
          </span>
        </div>
        {chain.overall_reasoning && (
          <p className="text-xs text-gray-400 mt-1 line-clamp-2">
            {chain.overall_reasoning}
          </p>
        )}
      </div>

      <div className="p-4 space-y-2">
        {chain.stages.map((stage, index) => (
          <StageCard
            key={stage.stage}
            result={stage}
            isLast={index === chain.stages.length - 1}
          />
        ))}
      </div>
    </div>
  );
}

export const ReasoningPanel = memo(ReasoningPanelInner);
