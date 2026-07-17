/**
 * Agents page - monitor and manage all registered AI agents.
 *
 * Displays agent status, health scores, load, and capabilities.
 */

"use client";

import { useCallback, useEffect, useState } from "react";
import { RefreshCw, AlertTriangle } from "lucide-react";

import { AgentActivity } from "@/components/orchestration/agent-activity";
import { orchestrationAgentApi } from "@/lib/orchestration/api-client";
import type { RegisteredAgent } from "@/types/orchestration";

export default function AgentsPage() {
  const [agents, setAgents] = useState<RegisteredAgent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAgents = useCallback(async () => {
    try {
      setLoading(true);
      const data = await orchestrationAgentApi.listAgents();
      setAgents(data);
      setError(null);
    } catch {
      setError("Failed to load agents");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAgents();
    const interval = setInterval(fetchAgents, 10_000);
    return () => clearInterval(interval);
  }, [fetchAgents]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-200">
            Agent Registry
          </h2>
          <p className="text-sm text-gray-500 mt-1">
            {agents.length} agents registered in the orchestration engine.
          </p>
        </div>
        <button
          type="button"
          onClick={fetchAgents}
          disabled={loading}
          className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium border border-gray-700 text-gray-400 hover:text-gray-200 hover:border-gray-600 transition-colors disabled:opacity-50"
        >
          <RefreshCw
            className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`}
          />
          Refresh
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/5 p-4 flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-red-400 flex-shrink-0" />
          <p className="text-sm text-red-400">{error}</p>
        </div>
      )}

      <AgentActivity agents={agents} />
    </div>
  );
}
