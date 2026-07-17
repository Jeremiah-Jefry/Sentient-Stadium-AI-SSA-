/**
 * EntityMarker - Renders a single entity on the digital twin map.
 *
 * Displays operational status color, entity type icon, capacity bar,
 * and health indicator. Supports hover, click, and selection states.
 */

"use client";

import { memo, useCallback } from "react";

import { STATUS_COLORS, HEALTH_COLORS, ENTITY_ICONS, getCapacityColor } from "./constants";
import type { EntitySummary } from "@/types/digital-twin";

interface EntityMarkerProps {
  entity: EntitySummary;
  isSelected: boolean;
  onSelect: (entityId: string) => void;
  onHover: (entityId: string | null) => void;
  zoomLevel: number;
}

function EntityMarkerInner({
  entity,
  isSelected,
  onSelect,
  onHover,
  zoomLevel,
}: EntityMarkerProps) {
  const handleClick = useCallback(
    () => onSelect(entity.id),
    [entity.id, onSelect],
  );

  const handleMouseEnter = useCallback(
    () => onHover(entity.id),
    [entity.id, onHover],
  );

  const handleMouseLeave = useCallback(
    () => onHover(null),
    [onHover],
  );

  const capacityPct =
    entity.max_capacity > 0
      ? Math.round((entity.current_capacity / entity.max_capacity) * 100)
      : 0;

  const statusColor = STATUS_COLORS[entity.operational_status];
  const healthRing = HEALTH_COLORS[entity.current_health];
  const iconLabel = ENTITY_ICONS[entity.entity_type];
  const capacityTextColor = getCapacityColor(
    entity.current_capacity,
    entity.max_capacity,
  );

  return (
    <button
      type="button"
      onClick={handleClick}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      className={`
        absolute flex flex-col items-center gap-0.5
        transition-all duration-150 ease-out
        focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400
        ${isSelected ? "scale-125 z-30" : "z-20 hover:scale-110"}
      `}
      style={{
        left: `${entity.coordinates_lon}%`,
        top: `${entity.coordinates_lat}%`,
        transform: "translate(-50%, -50%)",
      }}
      aria-label={`${entity.name} - ${entity.entity_type} - ${entity.operational_status}`}
    >
      {/* Status dot */}
      <span
        className={`
          block w-3 h-3 rounded-full ring-2 ${statusColor} ${healthRing}
          shadow-lg
        `}
      />

      {/* Label (visible at higher zoom) */}
      {zoomLevel > 2 && (
        <span className="text-[10px] text-gray-300 bg-gray-900/80 px-1 rounded whitespace-nowrap">
          {iconLabel}
        </span>
      )}

      {/* Capacity bar (visible at highest zoom) */}
      {zoomLevel > 3 && entity.max_capacity > 0 && (
        <div className="flex items-center gap-1">
          <div className="w-12 h-1 bg-gray-700 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full ${statusColor}`}
              style={{ width: `${capacityPct}%` }}
            />
          </div>
          <span className={`text-[9px] ${capacityTextColor}`}>
            {capacityPct}%
          </span>
        </div>
      )}
    </button>
  );
}

export const EntityMarker = memo(EntityMarkerInner);
