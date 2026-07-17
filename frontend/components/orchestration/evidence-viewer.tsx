/**
 * EvidenceViewer - Evidence display component.
 *
 * Shows a list of evidence items with source, type, content, weight,
 * sorting by weight, filtering by type, and expandable details.
 */

"use client";

import { memo, useCallback, useMemo, useState } from "react";
import { ChevronDown, Filter, ArrowUpDown } from "lucide-react";

import type { EvidenceItem } from "@/types/orchestration";

interface EvidenceViewerProps {
  evidence: EvidenceItem[];
}

type SortOrder = "weight_desc" | "weight_asc" | "timestamp_desc";

function EvidenceViewerInner({ evidence }: EvidenceViewerProps) {
  const [sortOrder, setSortOrder] = useState<SortOrder>("weight_desc");
  const [activeFilter, setActiveFilter] = useState<string | null>(null);
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);

  const toggleExpand = useCallback(
    (index: number) =>
      setExpandedIndex((prev) => (prev === index ? null : index)),
    [],
  );

  const toggleSort = useCallback(() => {
    setSortOrder((prev) =>
      prev === "weight_desc" ? "weight_asc" : "weight_desc",
    );
  }, []);

  const evidenceTypes = useMemo(() => {
    const types = new Set(evidence.map((e) => e.type));
    return Array.from(types).sort();
  }, [evidence]);

  const filtered = useMemo(() => {
    let items = activeFilter
      ? evidence.filter((e) => e.type === activeFilter)
      : [...evidence];

    switch (sortOrder) {
      case "weight_desc":
        items.sort((a, b) => b.weight - a.weight);
        break;
      case "weight_asc":
        items.sort((a, b) => a.weight - b.weight);
        break;
      case "timestamp_desc":
        items.sort(
          (a, b) =>
            new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime(),
        );
        break;
    }

    return items;
  }, [evidence, sortOrder, activeFilter]);

  function getWeightColor(weight: number): string {
    if (weight > 0.7) return "text-emerald-400";
    if (weight > 0.4) return "text-amber-400";
    return "text-gray-400";
  }

  return (
    <div
      role="region"
      aria-label="Evidence viewer"
      className="rounded-lg border border-gray-800 bg-gray-900/50 overflow-hidden"
    >
      <div className="px-4 py-3 border-b border-gray-800 bg-gray-900">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-200">
            Evidence
            <span className="ml-2 text-[10px] text-gray-500 font-normal">
              {filtered.length} items
            </span>
          </h3>
          <button
            type="button"
            onClick={toggleSort}
            className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] text-gray-400 bg-gray-800 border border-gray-700 hover:bg-gray-700 transition-colors cursor-pointer"
          >
            <ArrowUpDown className="h-3 w-3" />
            {sortOrder === "weight_desc" ? "Weight ↓" : "Weight ↑"}
          </button>
        </div>

        {evidenceTypes.length > 1 && (
          <div className="flex items-center gap-1.5 mt-2 flex-wrap">
            <Filter className="h-3 w-3 text-gray-500" />
            <button
              type="button"
              onClick={() => setActiveFilter(null)}
              className={`px-1.5 py-0.5 rounded text-[9px] font-semibold border transition-colors cursor-pointer ${
                activeFilter === null
                  ? "text-indigo-400 bg-indigo-500/10 border-indigo-500/30"
                  : "text-gray-500 bg-gray-800 border-gray-700 hover:text-gray-400"
              }`}
            >
              All
            </button>
            {evidenceTypes.map((t) => (
              <button
                key={t}
                type="button"
                onClick={() =>
                  setActiveFilter((prev) => (prev === t ? null : t))
                }
                className={`px-1.5 py-0.5 rounded text-[9px] font-semibold border transition-colors cursor-pointer ${
                  activeFilter === t
                    ? "text-indigo-400 bg-indigo-500/10 border-indigo-500/30"
                    : "text-gray-500 bg-gray-800 border-gray-700 hover:text-gray-400"
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="divide-y divide-gray-800">
        {filtered.map((item, index) => {
          const isExpanded = expandedIndex === index;

          return (
            <div key={index} className="transition-colors hover:bg-gray-800/30">
              <button
                type="button"
                onClick={() => toggleExpand(index)}
                aria-expanded={isExpanded}
                className="w-full flex items-center gap-3 px-4 py-2.5 text-left bg-transparent border-none cursor-pointer"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-semibold text-indigo-400 uppercase tracking-wider">
                      {item.type}
                    </span>
                    <span className="text-[10px] text-gray-500">
                      {item.source}
                    </span>
                  </div>
                  <p className="text-xs text-gray-300 mt-0.5 truncate">
                    {item.content}
                  </p>
                </div>

                <span
                  className={`text-[10px] font-mono tabular-nums font-semibold ${getWeightColor(
                    item.weight,
                  )}`}
                >
                  {(item.weight * 100).toFixed(0)}%
                </span>

                <ChevronDown
                  className={`h-3.5 w-3.5 text-gray-500 transition-transform duration-200 ${
                    isExpanded ? "rotate-180" : ""
                  }`}
                />
              </button>

              {isExpanded && (
                <div className="px-4 pb-3 pt-1 space-y-2 bg-gray-900/30">
                  <div className="grid grid-cols-3 gap-2 text-[10px]">
                    <div>
                      <span className="text-gray-500">Source</span>
                      <p className="text-gray-300 font-medium">{item.source}</p>
                    </div>
                    <div>
                      <span className="text-gray-500">Type</span>
                      <p className="text-gray-300 font-medium">{item.type}</p>
                    </div>
                    <div>
                      <span className="text-gray-500">Weight</span>
                      <p className="text-gray-300 font-medium font-mono">
                        {item.weight.toFixed(3)}
                      </p>
                    </div>
                  </div>
                  <div>
                    <span className="text-[10px] text-gray-500">Content</span>
                    <p className="text-xs text-gray-300 mt-0.5">
                      {item.content}
                    </p>
                  </div>
                  <div>
                    <span className="text-[10px] text-gray-500">Timestamp</span>
                    <p className="text-xs text-gray-400 font-mono">
                      {new Date(item.timestamp).toLocaleString()}
                    </p>
                  </div>
                  {Object.keys(item.metadata).length > 0 && (
                    <div>
                      <span className="text-[10px] text-gray-500">Metadata</span>
                      <pre className="mt-0.5 text-[10px] text-gray-400 bg-gray-800/50 rounded p-2 overflow-x-auto font-mono">
                        {JSON.stringify(item.metadata, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}

        {filtered.length === 0 && (
          <div className="px-4 py-8 text-center text-sm text-gray-500">
            No evidence items found.
          </div>
        )}
      </div>
    </div>
  );
}

export const EvidenceViewer = memo(EvidenceViewerInner);
