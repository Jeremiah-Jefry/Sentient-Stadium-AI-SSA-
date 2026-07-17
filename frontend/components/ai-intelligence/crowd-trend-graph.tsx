/**
 * CrowdTrendGraph - SVG line chart for crowd metric trends.
 *
 * Renders a simple line chart of risk score, density, or flow over time
 * using pure SVG with no external chart library dependency.
 */

"use client";

import { memo, useMemo } from "react";

interface DataPoint {
  timestamp: string;
  risk_score: number;
  density?: number;
  flow?: number;
}

interface CrowdTrendGraphProps {
  data: DataPoint[];
  metric?: "risk_score" | "density" | "flow";
}

const METRIC_LABELS: Record<string, string> = {
  risk_score: "Risk Score",
  density: "Density",
  flow: "Flow",
};

const CHART_PADDING = { top: 20, right: 20, bottom: 40, left: 50 };

function CrowdTrendGraphInner({ data, metric = "risk_score" }: CrowdTrendGraphProps) {
  const chartWidth = 600;
  const chartHeight = 200;
  const innerWidth = chartWidth - CHART_PADDING.left - CHART_PADDING.right;
  const innerHeight = chartHeight - CHART_PADDING.top - CHART_PADDING.bottom;

  const values = useMemo(
    () =>
      data
        .map((d) => d[metric])
        .filter((v): v is number => v !== undefined),
    [data, metric],
  );

  const maxValue = useMemo(() => {
    if (values.length === 0) return 1;
    return Math.max(...values) * 1.1 || 1;
  }, [values]);

  const minValue = useMemo(() => {
    if (values.length === 0) return 0;
    return Math.min(0, Math.min(...values));
  }, [values]);

  const range = maxValue - minValue || 1;

  const pathData = useMemo(() => {
    if (data.length < 2) return "";
    const points: string[] = [];

    data.forEach((d, idx) => {
      const value = d[metric];
      if (value === undefined) return;
      const x =
        CHART_PADDING.left + (idx / (data.length - 1)) * innerWidth;
      const y =
        CHART_PADDING.top +
        innerHeight -
        ((value - minValue) / range) * innerHeight;
      points.push(`${idx === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`);
    });

    return points.join(" ");
  }, [data, metric, innerWidth, innerHeight, minValue, range]);

  const areaPath = useMemo(() => {
    if (data.length < 2) return "";
    const points: string[] = [];

    data.forEach((d, idx) => {
      const value = d[metric];
      if (value === undefined) return;
      const x =
        CHART_PADDING.left + (idx / (data.length - 1)) * innerWidth;
      const y =
        CHART_PADDING.top +
        innerHeight -
        ((value - minValue) / range) * innerHeight;
      points.push(`${idx === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`);
    });

    const lastX = CHART_PADDING.left + innerWidth;
    const firstX = CHART_PADDING.left;
    const bottom = CHART_PADDING.top + innerHeight;

    return (
      points.join(" ") +
      ` L ${lastX.toFixed(2)} ${bottom} L ${firstX.toFixed(2)} ${bottom} Z`
    );
  }, [data, metric, innerWidth, innerHeight, minValue, range]);

  const yTicks = useMemo(() => {
    const tickCount = 4;
    const ticks: Array<{ y: number; label: string }> = [];
    for (let i = 0; i <= tickCount; i++) {
      const value = minValue + (range * i) / tickCount;
      const y =
        CHART_PADDING.top + innerHeight - (i / tickCount) * innerHeight;
      ticks.push({ y, label: value.toFixed(1) });
    }
    return ticks;
  }, [minValue, range, innerHeight]);

  const xLabels = useMemo(() => {
    if (data.length === 0) return [];
    const maxLabels = 6;
    const step = Math.max(1, Math.floor(data.length / maxLabels));
    const labels: Array<{ x: number; label: string }> = [];

    for (let i = 0; i < data.length; i += step) {
      const x = CHART_PADDING.left + (i / Math.max(data.length - 1, 1)) * innerWidth;
      const time = new Date(data[i]!.timestamp);
      labels.push({
        x,
        label: `${time.getHours().toString().padStart(2, "0")}:${time.getMinutes().toString().padStart(2, "0")}`,
      });
    }
    return labels;
  }, [data, innerWidth]);

  const metricLabel = METRIC_LABELS[metric];

  return (
    <div
      role="img"
      aria-label={`${metricLabel} trend chart with ${data.length} data points`}
      style={styles.container}
    >
      <svg
        width="100%"
        height="100%"
        viewBox={`0 0 ${chartWidth} ${chartHeight}`}
        preserveAspectRatio="xMidYMid meet"
      >
        {/* Y-axis grid lines and labels */}
        {yTicks.map((tick, idx) => (
          <g key={idx}>
            <line
              x1={CHART_PADDING.left}
              y1={tick.y}
              x2={CHART_PADDING.left + innerWidth}
              y2={tick.y}
              stroke="#2d2d44"
              strokeWidth={1}
            />
            <text
              x={CHART_PADDING.left - 8}
              y={tick.y}
              textAnchor="end"
              dominantBaseline="central"
              fill="#757575"
              fontSize={10}
              fontFamily="system-ui, sans-serif"
            >
              {tick.label}
            </text>
          </g>
        ))}

        {/* X-axis labels */}
        {xLabels.map((lbl, idx) => (
          <text
            key={idx}
            x={lbl.x}
            y={CHART_PADDING.top + innerHeight + 20}
            textAnchor="middle"
            fill="#757575"
            fontSize={10}
            fontFamily="system-ui, sans-serif"
          >
            {lbl.label}
          </text>
        ))}

        {/* Area fill */}
        {areaPath && (
          <path
            d={areaPath}
            fill="rgba(33, 150, 243, 0.08)"
          />
        )}

        {/* Line */}
        {pathData && (
          <path
            d={pathData}
            fill="none"
            stroke="#2196f3"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        )}

        {/* Data points */}
        {data.map((d, idx) => {
          const value = d[metric];
          if (value === undefined) return null;
          const x =
            CHART_PADDING.left +
            (idx / Math.max(data.length - 1, 1)) * innerWidth;
          const y =
            CHART_PADDING.top +
            innerHeight -
            ((value - minValue) / range) * innerHeight;
          return (
            <circle
              key={idx}
              cx={x}
              cy={y}
              r={2.5}
              fill="#2196f3"
              stroke="#0d1b2a"
              strokeWidth={1}
            />
          );
        })}

        {/* Y-axis label */}
        <text
          x={12}
          y={CHART_PADDING.top + innerHeight / 2}
          textAnchor="middle"
          fill="#9e9e9e"
          fontSize={11}
          fontFamily="system-ui, sans-serif"
          transform={`rotate(-90, 12, ${CHART_PADDING.top + innerHeight / 2})`}
        >
          {metricLabel}
        </text>
      </svg>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    backgroundColor: "#1a1a2e",
    border: "1px solid #2d2d44",
    borderRadius: 8,
    padding: 16,
    width: "100%",
  },
};

export const CrowdTrendGraph = memo(CrowdTrendGraphInner);
