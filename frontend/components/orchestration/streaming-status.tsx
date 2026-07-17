/**
 * StreamingStatus - Real-time streaming status indicator.
 *
 * Shows connection status, current pipeline stage, progress percentage,
 * last event timestamp, event count, and a cancel button.
 */

"use client";

import { memo } from "react";
import {
  Wifi,
  WifiOff,
  Loader2,
  X,
  Clock,
  Radio,
} from "lucide-react";

import type { PipelineStage, ExecutionStatus } from "@/types/orchestration";

interface StreamingStatusProps {
  connected: boolean;
  currentStage: PipelineStage | null;
  status: ExecutionStatus;
  progress: number;
  lastEventAt: string | null;
  eventCount: number;
  executionId: string;
  onCancel?: (executionId: string) => void;
}

const STAGE_LABELS: Record<PipelineStage, string> = {
  understand: "Understand",
  plan: "Plan",
  execute: "Execute",
  validate: "Validate",
  explain: "Explain",
  respond: "Respond",
};

function formatTimestamp(ts: string | null): string {
  if (!ts) return "—";
  const diff = Date.now() - new Date(ts).getTime();
  if (diff < 1000) return "just now";
  if (diff < 60_000) return `${Math.floor(diff / 1000)}s ago`;
  return `${Math.floor(diff / 60_000)}m ago`;
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

function StreamingStatusInner({
  connected,
  currentStage,
  status,
  progress,
  lastEventAt,
  eventCount,
  executionId,
  onCancel,
}: StreamingStatusProps) {
  const clampedProgress = Math.max(0, Math.min(100, Math.round(progress)));
  const isRunning = status === "executing" || status === "planning";
  const canCancel = isRunning && onCancel !== undefined;

  return (
    <div
      role="status"
      aria-label="Streaming status"
      className="flex items-center gap-3 px-4 py-2.5 rounded-lg border border-gray-800 bg-gray-900/50"
    >
      <div className="flex items-center gap-2">
        {connected ? (
          <div className="relative">
            <Wifi className="h-4 w-4 text-emerald-400" />
            {isRunning && (
              <span className="absolute -top-0.5 -right-0.5 h-2 w-2 rounded-full bg-indigo-500 animate-ping" />
            )}
          </div>
        ) : (
          <WifiOff className="h-4 w-4 text-red-400" />
        )}
        <span
          className={`text-[10px] font-semibold ${
            connected ? "text-emerald-400" : "text-red-400"
          }`}
        >
          {connected ? "Connected" : "Disconnected"}
        </span>
      </div>

      <div className="h-4 w-px bg-gray-700" />

      {currentStage && (
        <div className="flex items-center gap-2">
          <Loader2
            className={`h-3.5 w-3.5 text-indigo-400 ${
              isRunning ? "animate-spin" : ""
            }`}
          />
          <span className="text-[10px] text-gray-300 font-semibold">
            {STAGE_LABELS[currentStage]}
          </span>
        </div>
      )}

      <div className="flex-1 min-w-[100px]">
        <div className="flex items-center justify-between mb-0.5">
          <span className="text-[9px] text-gray-500 font-mono tabular-nums">
            {clampedProgress}%
          </span>
        </div>
        <div className="h-1 bg-gray-800 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-300 ${getStageColor(
              status,
            )}`}
            style={{ width: `${clampedProgress}%` }}
          />
        </div>
      </div>

      <div className="h-4 w-px bg-gray-700" />

      <div className="flex items-center gap-3 text-[10px] text-gray-500">
        <span className="flex items-center gap-1">
          <Radio className="h-3 w-3" />
          {eventCount}
        </span>
        <span className="flex items-center gap-1">
          <Clock className="h-3 w-3" />
          {formatTimestamp(lastEventAt)}
        </span>
      </div>

      {canCancel && (
        <>
          <div className="h-4 w-px bg-gray-700" />
          <button
            type="button"
            onClick={() => onCancel(executionId)}
            className="inline-flex items-center gap-1 px-2 py-1 rounded text-[10px] font-semibold text-red-400 bg-red-500/10 border border-red-500/30 hover:bg-red-500/20 transition-colors cursor-pointer"
          >
            <X className="h-3 w-3" />
            Cancel
          </button>
        </>
      )}
    </div>
  );
}

export const StreamingStatus = memo(StreamingStatusInner);
