/**
 * AITimeline - Visual pipeline stage timeline for orchestration.
 *
 * Shows each pipeline stage (Understand → Plan → Execute → Validate → Explain → Respond)
 * with current stage highlighted, completed stages with checkmarks, and per-stage duration.
 */

"use client";

import { memo, useMemo } from "react";
import { Check, Clock, Loader2, X } from "lucide-react";

import type { ExecutionStatus, PipelineStage } from "@/types/orchestration";

interface AITimelineProps {
  currentStage: PipelineStage;
  stageStatuses: Record<PipelineStage, ExecutionStatus>;
  stageDurations: Partial<Record<PipelineStage, number>>;
}

const PIPELINE_STAGES: PipelineStage[] = [
  "understand",
  "plan",
  "execute",
  "validate",
  "explain",
  "respond",
];

const STAGE_LABELS: Record<PipelineStage, string> = {
  understand: "Understand",
  plan: "Plan",
  execute: "Execute",
  validate: "Validate",
  explain: "Explain",
  respond: "Respond",
};

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function StatusIcon({ status }: { status: ExecutionStatus }) {
  if (status === "completed")
    return <Check className="h-3.5 w-3.5 text-emerald-400" />;
  if (status === "failed")
    return <X className="h-3.5 w-3.5 text-red-400" />;
  if (status === "executing" || status === "planning")
    return <Loader2 className="h-3.5 w-3.5 text-indigo-400 animate-spin" />;
  return <Clock className="h-3.5 w-3.5 text-gray-500" />;
}

function getStageColor(status: ExecutionStatus): string {
  switch (status) {
    case "completed":
      return "bg-emerald-500";
    case "executing":
    case "planning":
      return "bg-indigo-500";
    case "failed":
      return "bg-red-500";
    case "cancelled":
      return "bg-gray-500";
    default:
      return "bg-gray-700";
  }
}

function getStageBg(status: ExecutionStatus): string {
  switch (status) {
    case "completed":
      return "border-emerald-500/30 bg-emerald-500/5";
    case "executing":
    case "planning":
      return "border-indigo-500/30 bg-indigo-500/5";
    case "failed":
      return "border-red-500/30 bg-red-500/5";
    default:
      return "border-gray-700 bg-gray-900/50";
  }
}

function AITimelineInner({
  currentStage,
  stageStatuses,
  stageDurations,
}: AITimelineProps) {
  const currentIndex = useMemo(
    () => PIPELINE_STAGES.indexOf(currentStage),
    [currentStage],
  );

  return (
    <div
      role="list"
      aria-label="Orchestration pipeline timeline"
      className="flex items-start gap-0 w-full overflow-x-auto"
    >
      {PIPELINE_STAGES.map((stage, index) => {
        const status = stageStatuses[stage] ?? "pending";
        const duration = stageDurations[stage];
        const isActive = index === currentIndex;
        const isCompleted = status === "completed";

        return (
          <div
            key={stage}
            role="listitem"
            aria-current={isActive ? "step" : undefined}
            className="flex-1 flex flex-col items-center min-w-[100px]"
          >
            <div className="flex items-center w-full">
              <div className="flex-1 h-0.5">
                {index > 0 && (
                  <div
                    className={`h-full transition-colors duration-300 ${
                      isCompleted || isActive
                        ? "bg-indigo-500"
                        : "bg-gray-700"
                    }`}
                  />
                )}
              </div>

              <div
                className={`relative flex items-center justify-center w-8 h-8 rounded-full border-2 transition-all duration-300 ${getStageBg(
                  status,
                )} ${
                  isActive
                    ? "border-indigo-500 shadow-lg shadow-indigo-500/20"
                    : isCompleted
                      ? "border-emerald-500"
                      : "border-gray-700"
                }`}
              >
                <StatusIcon status={status} />
                {isActive && (
                  <span className="absolute inset-0 rounded-full animate-ping bg-indigo-500/20" />
                )}
              </div>

              <div className="flex-1 h-0.5">
                {index < PIPELINE_STAGES.length - 1 && (
                  <div
                    className={`h-full transition-colors duration-300 ${
                      isCompleted ? "bg-indigo-500" : "bg-gray-700"
                    }`}
                  />
                )}
              </div>
            </div>

            <div className="mt-2 text-center">
              <p
                className={`text-xs font-semibold transition-colors duration-300 ${
                  isActive
                    ? "text-indigo-400"
                    : isCompleted
                      ? "text-emerald-400"
                      : status === "failed"
                        ? "text-red-400"
                        : "text-gray-500"
                }`}
              >
                {STAGE_LABELS[stage]}
              </p>
              <div
                className={`h-1 w-8 mx-auto mt-1 rounded-full transition-colors duration-300 ${getStageColor(
                  status,
                )}`}
              />
              {duration !== undefined && (
                <p className="text-[10px] text-gray-500 mt-0.5 font-mono tabular-nums">
                  {formatDuration(duration)}
                </p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export const AITimeline = memo(AITimelineInner);
