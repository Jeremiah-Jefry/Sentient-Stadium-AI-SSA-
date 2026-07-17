/**
 * AgentActivity - Real-time agent activity dashboard.
 *
 * Displays all registered agents with status badges, health scores,
 * current load, capability tags, and last heartbeat timestamps.
 */

"use client";

import { memo } from "react";
import {
  Activity,
  Heart,
  Wifi,
  WifiOff,
  AlertTriangle,
  Wrench,
  Loader2,
  Circle,
} from "lucide-react";

import type { RegisteredAgent, AgentStatus } from "@/types/orchestration";

interface AgentActivityProps {
  agents: RegisteredAgent[];
}

const STATUS_CONFIG: Record<
  AgentStatus,
  { label: string; color: string; icon: typeof Activity }
> = {
  available: {
    label: "Available",
    color: "text-emerald-400 bg-emerald-500/10 border-emerald-500/30",
    icon: Wifi,
  },
  busy: {
    label: "Busy",
    color: "text-amber-400 bg-amber-500/10 border-amber-500/30",
    icon: Loader2,
  },
  degraded: {
    label: "Degraded",
    color: "text-orange-400 bg-orange-500/10 border-orange-500/30",
    icon: AlertTriangle,
  },
  offline: {
    label: "Offline",
    color: "text-gray-400 bg-gray-500/10 border-gray-500/30",
    icon: WifiOff,
  },
  error: {
    label: "Error",
    color: "text-red-400 bg-red-500/10 border-red-500/30",
    icon: AlertTriangle,
  },
  warming_up: {
    label: "Warming Up",
    color: "text-blue-400 bg-blue-500/10 border-blue-500/30",
    icon: Wrench,
  },
};

function formatTimestamp(ts: string): string {
  const diff = Date.now() - new Date(ts).getTime();
  if (diff < 60_000) return "just now";
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m ago`;
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}h ago`;
  return `${Math.floor(diff / 86_400_000)}d ago`;
}

function formatHealthScore(score: number): string {
  return `${Math.round(score * 100)}%`;
}

function getHealthBarColor(score: number): string {
  if (score > 0.8) return "bg-emerald-500";
  if (score > 0.5) return "bg-amber-500";
  return "bg-red-500";
}

function AgentCard({ agent }: { agent: RegisteredAgent }) {
  const config = STATUS_CONFIG[agent.status];
  const StatusIcon = config.icon;
  const loadPercent =
    agent.max_load > 0
      ? Math.round((agent.current_load / agent.max_load) * 100)
      : 0;

  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900/50 p-4 transition-colors hover:border-gray-700">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="flex-shrink-0 flex items-center justify-center w-8 h-8 rounded-lg bg-gray-800 border border-gray-700">
            <Activity className="h-4 w-4 text-gray-400" />
          </div>
          <div className="min-w-0">
            <h4 className="text-sm font-semibold text-gray-200 truncate">
              {agent.metadata.display_name}
            </h4>
            <p className="text-[10px] text-gray-500 truncate">
              {agent.metadata.name} v{agent.metadata.version}
            </p>
          </div>
        </div>

        <span
          className={`flex-shrink-0 inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold border ${config.color}`}
        >
          <StatusIcon
            className={`h-3 w-3 ${
              agent.status === "busy" || agent.status === "warming_up"
                ? "animate-spin"
                : ""
            }`}
          />
          {config.label}
        </span>
      </div>

      <p className="text-xs text-gray-400 mt-2 line-clamp-2">
        {agent.metadata.description}
      </p>

      <div className="mt-3 space-y-2">
        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-[10px] text-gray-500 uppercase tracking-wider font-semibold">
              Health
            </span>
            <span className="text-[10px] text-gray-400 font-mono tabular-nums">
              {formatHealthScore(agent.health_score)}
            </span>
          </div>
          <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${getHealthBarColor(
                agent.health_score,
              )}`}
              style={{ width: `${Math.round(agent.health_score * 100)}%` }}
            />
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-[10px] text-gray-500 uppercase tracking-wider font-semibold">
              Load
            </span>
            <span className="text-[10px] text-gray-400 font-mono tabular-nums">
              {agent.current_load}/{agent.max_load} ({loadPercent}%)
            </span>
          </div>
          <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                loadPercent > 80
                  ? "bg-red-500"
                  : loadPercent > 50
                    ? "bg-amber-500"
                    : "bg-indigo-500"
              }`}
              style={{ width: `${loadPercent}%` }}
            />
          </div>
        </div>
      </div>

      <div className="mt-3 flex flex-wrap gap-1">
        {agent.metadata.capabilities.slice(0, 4).map((cap) => (
          <span
            key={cap}
            className="inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-medium bg-gray-800 text-gray-400 border border-gray-700"
          >
            {cap}
          </span>
        ))}
        {agent.metadata.capabilities.length > 4 && (
          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-medium bg-gray-800 text-gray-500">
            +{agent.metadata.capabilities.length - 4}
          </span>
        )}
      </div>

      <div className="mt-3 flex items-center justify-between text-[10px] text-gray-500 border-t border-gray-800 pt-2">
        <span className="flex items-center gap-1">
          <Heart className="h-3 w-3" />
          {formatTimestamp(agent.last_heartbeat)}
        </span>
        <span className="flex items-center gap-1">
          <Circle className="h-2 w-2" />
          {agent.total_executions} runs &middot;{" "}
          {Math.round(agent.success_rate * 100)}% success
        </span>
        <span className="font-mono tabular-nums">
          {Math.round(agent.avg_response_ms)}ms avg
        </span>
      </div>
    </div>
  );
}

function AgentActivityInner({ agents }: AgentActivityProps) {
  const sorted = [...agents].sort((a, b) => {
    const order: Record<AgentStatus, number> = {
      error: 0,
      offline: 1,
      degraded: 2,
      busy: 3,
      warming_up: 4,
      available: 5,
    };
    return order[b.status] - order[a.status];
  });

  return (
    <div
      role="region"
      aria-label="Agent activity"
      className="rounded-lg border border-gray-800 bg-gray-900/50 overflow-hidden"
    >
      <div className="px-4 py-3 border-b border-gray-800 bg-gray-900 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-200">Agent Activity</h3>
        <span className="text-[10px] text-gray-500 font-mono">
          {agents.filter((a) => a.status === "available").length}/
          {agents.length} available
        </span>
      </div>

      <div className="p-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {sorted.map((agent) => (
          <AgentCard key={agent.name} agent={agent} />
        ))}
      </div>
    </div>
  );
}

export const AgentActivity = memo(AgentActivityInner);
