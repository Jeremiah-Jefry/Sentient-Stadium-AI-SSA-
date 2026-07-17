/**
 * ExecutionGraph - Visual graph of agent execution flow.
 *
 * Renders nodes for each agent step with edges showing dependencies,
 * color-coded by status (green=completed, blue=running, red=failed, gray=pending).
 * Uses a wave-based layout for parallel execution visualization.
 */

"use client";

import { memo, useMemo } from "react";
import {
  CheckCircle2,
  Clock,
  Loader2,
  AlertCircle,
  XCircle,
} from "lucide-react";

import type {
  ExecutionGraph as ExecutionGraphType,
  ExecutionStatus,
} from "@/types/orchestration";

interface ExecutionGraphProps {
  graph: ExecutionGraphType;
}

function formatDuration(ms: number | null): string {
  if (ms === null) return "—";
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function getStatusColor(status: ExecutionStatus): string {
  switch (status) {
    case "completed":
      return "border-emerald-500 bg-emerald-500/10 text-emerald-400";
    case "executing":
    case "planning":
      return "border-indigo-500 bg-indigo-500/10 text-indigo-400";
    case "failed":
      return "border-red-500 bg-red-500/10 text-red-400";
    case "cancelled":
      return "border-gray-500 bg-gray-500/10 text-gray-400";
    default:
      return "border-gray-700 bg-gray-800/50 text-gray-500";
  }
}

function getStatusIcon(status: ExecutionStatus) {
  switch (status) {
    case "completed":
      return <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />;
    case "executing":
    case "planning":
      return <Loader2 className="h-3.5 w-3.5 text-indigo-400 animate-spin" />;
    case "failed":
      return <XCircle className="h-3.5 w-3.5 text-red-400" />;
    case "cancelled":
      return <AlertCircle className="h-3.5 w-3.5 text-gray-400" />;
    default:
      return <Clock className="h-3.5 w-3.5 text-gray-500" />;
  }
}

function getEdgeColor(
  sourceStatus: ExecutionStatus,
  targetStatus: ExecutionStatus,
): string {
  if (sourceStatus === "completed" && targetStatus !== "pending")
    return "stroke-emerald-500";
  if (sourceStatus === "completed" && targetStatus === "pending")
    return "stroke-gray-600";
  if (sourceStatus === "failed") return "stroke-red-500/50";
  return "stroke-gray-700";
}

function ExecutionGraphInner({ graph }: ExecutionGraphProps) {
  const waves = useMemo(() => {
    const grouped = new Map<number, typeof graph.nodes>();
    for (const node of graph.nodes) {
      const existing = grouped.get(node.wave) ?? [];
      existing.push(node);
      grouped.set(node.wave, existing);
    }
    return Array.from(grouped.entries()).sort(([a], [b]) => a - b);
  }, [graph.nodes]);

  const nodeMap = useMemo(() => {
    const map = new Map<string, (typeof graph.nodes)[0]>();
    for (const node of graph.nodes) {
      map.set(node.id, node);
    }
    return map;
  }, [graph.nodes]);

  const svgWidth = useMemo(() => {
    if (waves.length === 0) return 0;
    const maxNodesInWave = Math.max(
      ...waves.map(([, nodes]) => nodes.length),
    );
    return Math.max(maxNodesInWave * 180 + 60, 400);
  }, [waves]);

  const svgHeight = useMemo(
    () => Math.max(waves.length * 120 + 40, 200),
    [waves.length],
  );

  const nodePositions = useMemo(() => {
    const positions = new Map<string, { x: number; y: number }>();
    for (const [waveIndex, [, nodes]] of waves.entries()) {
      const waveWidth = nodes.length * 180;
      const startX = (svgWidth - waveWidth) / 2 + 90;
      for (const [nodeIndex, node] of nodes.entries()) {
        positions.set(node.id, {
          x: startX + nodeIndex * 180,
          y: waveIndex * 120 + 60,
        });
      }
    }
    return positions;
  }, [waves, svgWidth]);

  return (
    <div
      role="img"
      aria-label="Agent execution flow graph"
      className="w-full overflow-x-auto rounded-lg border border-gray-800 bg-gray-900/50"
    >
      <svg
        width={svgWidth}
        height={svgHeight}
        viewBox={`0 0 ${svgWidth} ${svgHeight}`}
        className="min-w-[400px]"
      >
        {graph.edges.map((edge) => {
          const sourcePos = nodePositions.get(edge.source);
          const targetPos = nodePositions.get(edge.target);
          if (!sourcePos || !targetPos) return null;

          const sourceNode = nodeMap.get(edge.source);
          const targetNode = nodeMap.get(edge.target);
          if (!sourceNode || !targetNode) return null;

          const midY = (sourcePos.y + targetPos.y) / 2;
          const color = getEdgeColor(sourceNode.status, targetNode.status);

          return (
            <g key={`${edge.source}-${edge.target}`}>
              <path
                d={`M ${sourcePos.x} ${sourcePos.y + 28} C ${sourcePos.x} ${midY}, ${targetPos.x} ${midY}, ${targetPos.x} ${targetPos.y - 28}`}
                fill="none"
                stroke="currentColor"
                strokeWidth={1.5}
                className={color}
                markerEnd="url(#arrowhead)"
              />
            </g>
          );
        })}

        <defs>
          <marker
            id="arrowhead"
            markerWidth="8"
            markerHeight="6"
            refX="8"
            refY="3"
            orient="auto"
          >
            <polygon
              points="0 0, 8 3, 0 6"
              className="fill-gray-500"
            />
          </marker>
        </defs>

        {graph.nodes.map((node) => {
          const pos = nodePositions.get(node.id);
          if (!pos) return null;

          return (
            <g key={node.id}>
              <rect
                x={pos.x - 70}
                y={pos.y - 24}
                width={140}
                height={48}
                rx={8}
                className={`stroke-[1.5] ${getStatusColor(node.status)}`}
                strokeWidth={1.5}
              />
              <foreignObject
                x={pos.x - 66}
                y={pos.y - 22}
                width={132}
                height={44}
              >
                <div className="flex flex-col items-center justify-center h-full px-1">
                  <div className="flex items-center gap-1">
                    {getStatusIcon(node.status)}
                    <span className="text-[10px] font-semibold text-gray-200 truncate max-w-[100px]">
                      {node.agent_name}
                    </span>
                  </div>
                  <span className="text-[9px] text-gray-400 truncate max-w-[110px] mt-0.5">
                    {node.action}
                  </span>
                  {node.duration_ms !== null && (
                    <span className="text-[8px] text-gray-500 font-mono tabular-nums mt-0.5">
                      {formatDuration(node.duration_ms)}
                    </span>
                  )}
                </div>
              </foreignObject>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

export const ExecutionGraph = memo(ExecutionGraphInner);
