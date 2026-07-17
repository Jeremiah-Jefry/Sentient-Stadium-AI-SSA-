/**
 * Execute page - submit orchestration requests to the AI engine.
 *
 * Provides a form for volunteers and operators to submit requests
 * and view real-time orchestration results.
 */

"use client";

import { useCallback, useState } from "react";
import {
  Send,
  Loader2,
  XCircle,
  RotateCcw,
} from "lucide-react";

import { DecisionCard } from "@/components/orchestration/decision-card";
import { AITimeline } from "@/components/orchestration/ai-timeline";
import { ReasoningPanel } from "@/components/orchestration/reasoning-panel";
import { EvidenceViewer } from "@/components/orchestration/evidence-viewer";
import { useOrchestration } from "@/hooks/use-orchestration";
import type {
  OrchestratorRequest,
  OrchestratorResponse,
  RequestType,
  IntentType,
} from "@/types/orchestration";

const REQUEST_TYPES: Array<{ value: RequestType; label: string }> = [
  { value: "volunteer_request", label: "Volunteer Request" },
  { value: "admin_request", label: "Admin Request" },
  { value: "emergency", label: "Emergency" },
  { value: "accessibility_request", label: "Accessibility" },
  { value: "navigation_request", label: "Navigation" },
];

const INTENT_TYPES: Array<{ value: IntentType; label: string }> = [
  { value: "crowd_management", label: "Crowd Management" },
  { value: "navigation", label: "Navigation" },
  { value: "emergency_response", label: "Emergency Response" },
  { value: "accessibility", label: "Accessibility" },
  { value: "medical", label: "Medical" },
  { value: "resource_allocation", label: "Resource Allocation" },
  { value: "information_query", label: "Information Query" },
  { value: "incident_response", label: "Incident Response" },
  { value: "evacuation", label: "Evacuation" },
  { value: "weather_advisory", label: "Weather Advisory" },
  { value: "security", label: "Security" },
  { value: "operational", label: "Operational" },
];

const PRESET_QUERIES = [
  {
    label: "Gate B Overcrowding + Wheelchair",
    query:
      "Gate B is overcrowded and a wheelchair user needs help reaching Section D.",
    request_type: "volunteer_request" as RequestType,
    intent: "accessibility" as IntentType,
    priority: 8,
  },
  {
    label: "Medical Emergency",
    query:
      "Spectator collapsed in Section C Row 12. Possible cardiac event. Need medical team.",
    request_type: "emergency" as RequestType,
    intent: "medical" as IntentType,
    priority: 10,
  },
  {
    label: "Weather Evacuation",
    query:
      "Severe thunderstorm approaching. Need to evacuate outdoor sections within 30 minutes.",
    request_type: "emergency" as RequestType,
    intent: "evacuation" as IntentType,
    priority: 10,
  },
  {
    label: "Parking Guidance",
    query:
      "Where is the nearest accessible parking for a visitor with mobility equipment?",
    request_type: "navigation_request" as RequestType,
    intent: "navigation" as IntentType,
    priority: 5,
  },
];

function ResultSection({
  result,
}: {
  result: OrchestratorResponse;
}) {
  const [activeTab, setActiveTab] = useState<
    "timeline" | "reasoning" | "evidence"
  >("timeline");

  const tabs = [
    { id: "timeline" as const, label: "Timeline" },
    { id: "reasoning" as const, label: "Reasoning" },
    { id: "evidence" as const, label: "Evidence" },
  ];

  const stages = result.reasoning_chain.stages;
  const currentStage = (stages[stages.length - 1]?.stage ?? "observe") as import("@/types/orchestration").PipelineStage;
  const stageStatuses = Object.fromEntries(
    stages.map((s) => [s.stage, s.status]),
  ) as Record<import("@/types/orchestration").PipelineStage, import("@/types/orchestration").ExecutionStatus>;
  const stageDurations = Object.fromEntries(
    stages.filter((s) => s.duration_ms !== null).map((s) => [s.stage, s.duration_ms!]),
  );

  return (
    <div className="space-y-4">
      <DecisionCard decision={result} role="admin" />

      <div className="rounded-lg border border-gray-800 bg-gray-900/50 overflow-hidden">
        <div className="flex border-b border-gray-800">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 text-xs font-medium transition-colors ${
                activeTab === tab.id
                  ? "text-indigo-400 border-b-2 border-indigo-400 bg-indigo-500/5"
                  : "text-gray-500 hover:text-gray-300"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="p-4">
          {activeTab === "timeline" && (
            <AITimeline
              currentStage={currentStage}
              stageStatuses={stageStatuses}
              stageDurations={stageDurations}
            />
          )}
          {activeTab === "reasoning" && (
            <ReasoningPanel chain={result.reasoning_chain} />
          )}
          {activeTab === "evidence" && (
            <EvidenceViewer
              evidence={result.confidence_report.limiting_factors.map(
                (f, i) => ({
                  source: "system",
                  type: "analysis",
                  content: f,
                  weight: 0.5,
                  timestamp: new Date().toISOString(),
                  metadata: {},
                }),
              )}
            />
          )}
        </div>
      </div>
    </div>
  );
}

export default function ExecutePage() {
  const { execute, loading, error } = useOrchestration();
  const [query, setQuery] = useState("");
  const [requestType, setRequestType] = useState<RequestType>(
    "volunteer_request",
  );
  const [intent, setIntent] = useState<IntentType>("information_query");
  const [priority, setPriority] = useState(5);
  const [result, setResult] = useState<OrchestratorResponse | null>(null);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!query.trim()) return;

      const request: OrchestratorRequest = {
        request_type: requestType,
        intent,
        venue_id: "00000000-0000-0000-0000-000000000001",
        payload: { query },
        priority,
      };

      const response = await execute(request);
      if (response) setResult(response);
    },
    [query, requestType, intent, priority, execute],
  );

  const handlePreset = useCallback(
    (preset: (typeof PRESET_QUERIES)[number]) => {
      setQuery(preset.query);
      setRequestType(preset.request_type);
      setIntent(preset.intent);
      setPriority(preset.priority);
    },
    [],
  );

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-gray-200">
          Execute Orchestration
        </h2>
        <p className="text-sm text-gray-500 mt-1">
          Submit a request to the multi-agent AI orchestration engine.
        </p>
      </div>

      {/* Preset Queries */}
      <div className="rounded-lg border border-gray-800 bg-gray-900/50 p-4">
        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
          Quick Scenarios
        </h3>
        <div className="flex flex-wrap gap-2">
          {PRESET_QUERIES.map((preset) => (
            <button
              key={preset.label}
              type="button"
              onClick={() => handlePreset(preset)}
              className="px-3 py-1.5 rounded-md text-xs font-medium bg-gray-800 text-gray-300 border border-gray-700 hover:border-indigo-500/50 hover:text-indigo-400 transition-colors"
            >
              {preset.label}
            </button>
          ))}
        </div>
      </div>

      {/* Request Form */}
      <form
        onSubmit={handleSubmit}
        className="rounded-lg border border-gray-800 bg-gray-900/50 p-4 space-y-4"
      >
        <div>
          <label
            htmlFor="query"
            className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1.5"
          >
            Request
          </label>
          <textarea
            id="query"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Describe the situation or request..."
            rows={3}
            className="w-full rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-200 placeholder:text-gray-600 focus:outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/20 resize-none"
          />
        </div>

        <div className="grid gap-4 sm:grid-cols-3">
          <div>
            <label
              htmlFor="request-type"
              className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1.5"
            >
              Type
            </label>
            <select
              id="request-type"
              value={requestType}
              onChange={(e) =>
                setRequestType(e.target.value as RequestType)
              }
              className="w-full rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-indigo-500/50"
            >
              {REQUEST_TYPES.map((rt) => (
                <option key={rt.value} value={rt.value}>
                  {rt.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label
              htmlFor="intent"
              className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1.5"
            >
              Intent
            </label>
            <select
              id="intent"
              value={intent}
              onChange={(e) => setIntent(e.target.value as IntentType)}
              className="w-full rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-indigo-500/50"
            >
              {INTENT_TYPES.map((it) => (
                <option key={it.value} value={it.value}>
                  {it.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label
              htmlFor="priority"
              className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1.5"
            >
              Priority ({priority})
            </label>
            <input
              id="priority"
              type="range"
              min={1}
              max={10}
              value={priority}
              onChange={(e) => setPriority(Number(e.target.value))}
              className="w-full mt-2 accent-indigo-500"
            />
            <div className="flex justify-between text-[10px] text-gray-600 mt-0.5">
              <span>Low</span>
              <span>Critical</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium bg-indigo-600 text-white hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
            {loading ? "Processing..." : "Execute"}
          </button>

          {result && (
            <button
              type="button"
              onClick={() => {
                setResult(null);
                setQuery("");
              }}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium border border-gray-700 text-gray-400 hover:text-gray-200 hover:border-gray-600 transition-colors"
            >
              <RotateCcw className="h-4 w-4" />
              New Request
            </button>
          )}
        </div>

        {error && (
          <div className="flex items-center gap-2 p-3 rounded-md bg-red-500/10 border border-red-500/20">
            <XCircle className="h-4 w-4 text-red-400 flex-shrink-0" />
            <p className="text-sm text-red-400">{error}</p>
          </div>
        )}
      </form>

      {/* Results */}
      {result && <ResultSection result={result} />}
    </div>
  );
}
