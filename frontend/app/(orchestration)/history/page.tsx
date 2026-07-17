/**
 * History page - browse past orchestration executions.
 *
 * Displays paginated execution history with status, confidence, and duration.
 */

"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Clock,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";

import {
  orchestrationApi,
  type ExecutionDetailResponse,
  type PaginatedResponse,
} from "@/lib/orchestration/api-client";
import type { ExecutionStatus } from "@/types/orchestration";

const STATUS_CONFIG: Record<
  ExecutionStatus,
  { label: string; color: string; icon: typeof CheckCircle2 }
> = {
  completed: {
    label: "Completed",
    color: "text-emerald-400",
    icon: CheckCircle2,
  },
  failed: { label: "Failed", color: "text-red-400", icon: XCircle },
  cancelled: {
    label: "Cancelled",
    color: "text-gray-400",
    icon: AlertTriangle,
  },
  timeout: {
    label: "Timeout",
    color: "text-amber-400",
    icon: AlertTriangle,
  },
  pending: { label: "Pending", color: "text-gray-500", icon: Clock },
  planning: { label: "Planning", color: "text-indigo-400", icon: Clock },
  executing: {
    label: "Executing",
    color: "text-indigo-400",
    icon: Clock,
  },
  aggregating: {
    label: "Aggregating",
    color: "text-indigo-400",
    icon: Clock,
  },
  validating: {
    label: "Validating",
    color: "text-indigo-400",
    icon: Clock,
  },
};

function formatDuration(ms: number | null): string {
  if (ms === null) return "\u2014";
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function ExecutionRow({
  execution,
}: {
  execution: ExecutionDetailResponse;
}) {
  const statusKey = execution.status as ExecutionStatus;
  const config = STATUS_CONFIG[statusKey] ?? STATUS_CONFIG.pending;
  const StatusIcon = config.icon;
  const confidence = execution.confidence;
  const confidencePercent =
    confidence !== null ? Math.round(confidence * 100) : null;

  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900/50 p-4 hover:border-gray-700 transition-colors">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className={`flex items-center gap-1 text-xs font-semibold ${config.color}`}>
              <StatusIcon className="h-3.5 w-3.5" />
              {config.label}
            </span>
            {execution.strategy && (
              <span className="text-[10px] text-gray-500 font-mono bg-gray-800 px-1.5 py-0.5 rounded">
                {execution.strategy}
              </span>
            )}
          </div>
          <p className="text-xs text-gray-400 mt-1 truncate">
            {execution.recommendation ?? "No recommendation"}
          </p>
          <div className="flex items-center gap-3 mt-2 text-[10px] text-gray-500">
            <span className="font-mono">
              {execution.id.slice(0, 8)}
            </span>
            <span>
              {execution.steps_completed} steps completed
              {execution.steps_failed > 0 && (
                <span className="text-red-400">
                  {" "}
                  / {execution.steps_failed} failed
                </span>
              )}
            </span>
            <span>{formatDuration(execution.total_duration_ms)}</span>
          </div>
        </div>

        {confidencePercent !== null && (
          <div className="flex-shrink-0 text-right">
            <span
              className={`text-sm font-bold font-mono ${
                confidencePercent > 80
                  ? "text-emerald-400"
                  : confidencePercent > 50
                    ? "text-amber-400"
                    : "text-red-400"
              }`}
            >
              {confidencePercent}%
            </span>
            <p className="text-[10px] text-gray-600">confidence</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default function HistoryPage() {
  const [data, setData] = useState<
    PaginatedResponse<ExecutionDetailResponse> | null
  >(null);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<ExecutionStatus | "">("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchHistory = useCallback(async () => {
    try {
      setLoading(true);
      const result = await orchestrationApi.getExecutionHistory({
        page,
        page_size: 20,
        ...(statusFilter ? { status: statusFilter } : {}),
      });
      setData(result);
      setError(null);
    } catch {
      setError("Failed to load execution history");
    } finally {
      setLoading(false);
    }
  }, [page, statusFilter]);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-gray-200">
          Execution History
        </h2>
        <p className="text-sm text-gray-500 mt-1">
          Browse past orchestration executions and their outcomes.
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/5 p-4 flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-red-400 flex-shrink-0" />
          <p className="text-sm text-red-400">{error}</p>
        </div>
      )}

      {/* Filter */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-gray-500">Filter:</span>
        {["", "completed", "failed", "cancelled", "timeout"].map((status) => (
          <button
            key={status}
            type="button"
            onClick={() => {
              setStatusFilter(status as ExecutionStatus | "");
              setPage(1);
            }}
            className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
              statusFilter === status
                ? "bg-indigo-500/10 text-indigo-400 border border-indigo-500/20"
                : "text-gray-500 border border-gray-800 hover:text-gray-300 hover:border-gray-700"
            }`}
          >
            {status || "All"}
          </button>
        ))}
      </div>

      {/* Results */}
      {loading ? (
        <div className="flex items-center justify-center h-32">
          <div className="text-sm text-gray-500">Loading history...</div>
        </div>
      ) : data && data.items.length > 0 ? (
        <>
          <div className="space-y-2">
            {data.items.map((execution) => (
              <ExecutionRow key={execution.id} execution={execution} />
            ))}
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between">
            <p className="text-xs text-gray-500">
              Showing {(page - 1) * 20 + 1}-
              {Math.min(page * 20, data.total)} of {data.total}
            </p>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="p-1.5 rounded border border-gray-700 text-gray-400 hover:text-gray-200 disabled:opacity-30 transition-colors"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <span className="text-xs text-gray-500 font-mono">
                {page} / {data.total_pages}
              </span>
              <button
                type="button"
                onClick={() => setPage((p) => p + 1)}
                disabled={page >= data.total_pages}
                className="p-1.5 rounded border border-gray-700 text-gray-400 hover:text-gray-200 disabled:opacity-30 transition-colors"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        </>
      ) : (
        <div className="text-center py-12 text-sm text-gray-500">
          No executions found.
        </div>
      )}
    </div>
  );
}
