/**
 * Orchestration dashboard - main overview of the AI orchestration engine.
 *
 * Displays system health, agent activity, metrics summary, and recent decisions.
 */

"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Activity,
  Brain,
  Shield,
  Users,
  TrendingUp,
  AlertTriangle,
} from "lucide-react";

import { AgentActivity } from "@/components/orchestration/agent-activity";
import { ConfidenceMeter } from "@/components/orchestration/confidence-meter";
import {
  orchestrationAgentApi,
  orchestrationMonitoringApi,
} from "@/lib/orchestration/api-client";
import type {
  RegisteredAgent,
  MetricsSummary,
} from "@/types/orchestration";

interface SystemHealth {
  status: "healthy" | "degraded" | "unhealthy";
  execution_health: Record<string, string>;
  metrics_summary: {
    total_executions: number;
    success_rate: number;
    avg_confidence: number;
  };
}

function MetricCard({
  label,
  value,
  icon: Icon,
  color,
}: {
  label: string;
  value: string;
  icon: typeof Activity;
  color: string;
}) {
  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900/50 p-4">
      <div className="flex items-center gap-3">
        <div
          className={`flex items-center justify-center w-10 h-10 rounded-lg ${color}`}
        >
          <Icon className="h-5 w-5" />
        </div>
        <div>
          <p className="text-[10px] text-gray-500 uppercase tracking-wider font-semibold">
            {label}
          </p>
          <p className="text-lg font-bold text-gray-200 font-mono tabular-nums">
            {value}
          </p>
        </div>
      </div>
    </div>
  );
}

function OrchestratorDashboardContent() {
  const [agents, setAgents] = useState<RegisteredAgent[]>([]);
  const [metrics, setMetrics] = useState<MetricsSummary | null>(null);
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const [agentsData, metricsData, healthData] = await Promise.allSettled([
        orchestrationAgentApi.listAgents(),
        orchestrationMonitoringApi.getMetrics(),
        orchestrationMonitoringApi.getSystemHealth(),
      ]);

      if (agentsData.status === "fulfilled") setAgents(agentsData.value);
      if (metricsData.status === "fulfilled") setMetrics(metricsData.value);
      if (healthData.status === "fulfilled") setHealth(healthData.value);

      setError(null);
    } catch {
      setError("Failed to load orchestration data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 15_000);
    return () => clearInterval(interval);
  }, [fetchData]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-sm text-gray-500">Loading orchestration engine...</div>
      </div>
    );
  }

  const availableAgents = agents.filter((a) => a.status === "available").length;
  const avgConfidence = metrics?.avg_confidence ?? 0;
  const successRate = metrics?.success_rate ?? 0;

  return (
    <div className="space-y-6">
      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/5 p-4 flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-red-400 flex-shrink-0" />
          <p className="text-sm text-red-400">{error}</p>
        </div>
      )}

      {/* System Status */}
      <div className="flex items-center gap-3">
        <div
          className={`w-2.5 h-2.5 rounded-full ${
            health?.status === "healthy"
              ? "bg-emerald-400"
              : health?.status === "degraded"
                ? "bg-amber-400"
                : "bg-red-400"
          }`}
        />
        <span className="text-sm text-gray-400">
          System {health?.status ?? "unknown"}
        </span>
      </div>

      {/* Metrics Row */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          label="Total Executions"
          value={String(metrics?.total_executions ?? 0)}
          icon={Activity}
          color="bg-indigo-500/10 text-indigo-400"
        />
        <MetricCard
          label="Active Agents"
          value={`${availableAgents}/${agents.length}`}
          icon={Users}
          color="bg-emerald-500/10 text-emerald-400"
        />
        <MetricCard
          label="Avg Confidence"
          value={`${Math.round(avgConfidence * 100)}%`}
          icon={Brain}
          color="bg-purple-500/10 text-purple-400"
        />
        <MetricCard
          label="Success Rate"
          value={`${Math.round(successRate * 100)}%`}
          icon={TrendingUp}
          color="bg-cyan-500/10 text-cyan-400"
        />
      </div>

      {/* Confidence + Safety Row */}
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-lg border border-gray-800 bg-gray-900/50 p-4">
          <div className="flex items-center gap-2 mb-4">
            <Brain className="h-4 w-4 text-purple-400" />
            <h3 className="text-sm font-semibold text-gray-200">
              Confidence Overview
            </h3>
          </div>
          <ConfidenceMeter
            report={{
              overall: avgConfidence,
              per_agent: {},
              agreement_score: metrics?.avg_confidence ?? 0,
              reasoning_quality: 0.8,
              evidence_strength: 0.75,
              safety_confidence: 0.9,
              knowledge_base_coverage: 0.7,
              limiting_factors: [],
            }}
          />
        </div>

        <div className="rounded-lg border border-gray-800 bg-gray-900/50 p-4">
          <div className="flex items-center gap-2 mb-4">
            <Shield className="h-4 w-4 text-emerald-400" />
            <h3 className="text-sm font-semibold text-gray-200">
              Safety Status
            </h3>
          </div>
          <div className="space-y-3">
            {Object.entries(health?.execution_health ?? {}).map(
              ([key, status]) => (
                <div
                  key={key}
                  className="flex items-center justify-between p-2 rounded bg-gray-800/50"
                >
                  <span className="text-xs text-gray-400 capitalize">
                    {key.replace(/_/g, " ")}
                  </span>
                  <span
                    className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                      status === "healthy"
                        ? "text-emerald-400 bg-emerald-500/10"
                        : "text-amber-400 bg-amber-500/10"
                    }`}
                  >
                    {status}
                  </span>
                </div>
              ),
            )}
          </div>
        </div>
      </div>

      {/* Agent Activity */}
      <AgentActivity agents={agents} />
    </div>
  );
}

export default function OrchestrationDashboardPage() {
  return <OrchestratorDashboardContent />;
}
