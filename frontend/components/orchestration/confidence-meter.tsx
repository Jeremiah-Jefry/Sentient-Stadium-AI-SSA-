/**
 * ConfidenceMeter - Visual confidence display for orchestration.
 *
 * Shows overall confidence as a circular progress indicator with
 * breakdown bars for per-agent, agreement, reasoning, evidence,
 * safety, and knowledge scores, plus limiting factors.
 */

"use client";

import { memo, useMemo } from "react";
import { AlertTriangle } from "lucide-react";

import type { ConfidenceReport } from "@/types/orchestration";

interface ConfidenceMeterProps {
  report: ConfidenceReport;
  size?: "sm" | "md" | "lg";
}

const SIZE_CONFIG: Record<
  "sm" | "md" | "lg",
  { canvas: number; stroke: number; fontSize: number }
> = {
  sm: { canvas: 48, stroke: 4, fontSize: 11 },
  md: { canvas: 80, stroke: 6, fontSize: 16 },
  lg: { canvas: 120, stroke: 8, fontSize: 24 },
};

function getConfidenceColor(value: number): string {
  if (value > 0.8) return "#4caf50";
  if (value > 0.5) return "#ff9800";
  return "#f44336";
}

function ConfidenceMeterInner({ report, size = "md" }: ConfidenceMeterProps) {
  const config = SIZE_CONFIG[size];
  const radius = (config.canvas - config.stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const clamped = Math.max(0, Math.min(1, report.overall));
  const offset = circumference * (1 - clamped);
  const color = getConfidenceColor(clamped);
  const percentage = Math.round(clamped * 100);

  const breakdownEntries = useMemo(
    () => [
      { label: "Per-Agent", value: averageValues(report.per_agent) },
      { label: "Agreement", value: report.agreement_score },
      { label: "Reasoning", value: report.reasoning_quality },
      { label: "Evidence", value: report.evidence_strength },
      { label: "Safety", value: report.safety_confidence },
      { label: "Knowledge", value: report.knowledge_base_coverage },
    ],
    [report],
  );

  return (
    <div
      role="meter"
      aria-label={`Confidence: ${percentage}%`}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={percentage}
      className="inline-flex items-center gap-4"
    >
      <div className="relative">
        <svg
          width={config.canvas}
          height={config.canvas}
          viewBox={`0 0 ${config.canvas} ${config.canvas}`}
          aria-hidden="true"
        >
          <circle
            cx={config.canvas / 2}
            cy={config.canvas / 2}
            r={radius}
            fill="none"
            stroke="#1f2937"
            strokeWidth={config.stroke}
          />
          <circle
            cx={config.canvas / 2}
            cy={config.canvas / 2}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth={config.stroke}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            className="transition-[stroke-dashoffset] duration-500 ease-out"
            style={{
              transform: "rotate(-90deg)",
              transformOrigin: "center",
            }}
          />
          <text
            x="50%"
            y="50%"
            textAnchor="middle"
            dominantBaseline="central"
            fill="#f3f4f6"
            fontSize={config.fontSize}
            fontWeight={700}
            fontFamily="system-ui, sans-serif"
          >
            {percentage}%
          </text>
        </svg>
      </div>

      <div className="flex flex-col gap-1.5 min-w-[140px]">
        {breakdownEntries.map((entry) => (
          <div key={entry.label} className="flex items-center gap-2">
            <span className="text-[10px] text-gray-400 w-16 shrink-0">
              {entry.label}
            </span>
            <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-400 ease-out"
                style={{
                  width: `${Math.round(entry.value * 100)}%`,
                  backgroundColor: getConfidenceColor(entry.value),
                }}
              />
            </div>
            <span className="text-[10px] text-gray-400 font-mono tabular-nums w-8 text-right shrink-0">
              {Math.round(entry.value * 100)}%
            </span>
          </div>
        ))}
      </div>

      {report.limiting_factors.length > 0 && (
        <div className="flex flex-col gap-1 max-w-[200px]">
          {report.limiting_factors.map((factor) => (
            <div
              key={factor}
              className="flex items-center gap-1.5 text-[10px] text-amber-400"
            >
              <AlertTriangle className="h-3 w-3 flex-shrink-0" />
              <span className="truncate">{factor}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function averageValues(record: Record<string, number>): number {
  const values = Object.values(record);
  if (values.length === 0) return 0;
  return values.reduce((sum, v) => sum + v, 0) / values.length;
}

export const ConfidenceMeter = memo(ConfidenceMeterInner);
