/**
 * MapOverlayControls - Filter and overlay toggles for the digital twin map.
 *
 * Provides entity type filtering, overlay layers (accessibility, emergency,
 * crowd, medical, transport), and view mode controls.
 */

"use client";

import { memo, useCallback } from "react";

import type { EntityType, OperationalStatus, EntityHealth } from "@/types/digital-twin";

interface OverlayFilters {
  entityTypes: EntityType[];
  operationalStatus: OperationalStatus[];
  healthStatus: EntityHealth[];
  accessibilityOverlay: boolean;
  emergencyOverlay: boolean;
  crowdOverlay: boolean;
}

interface MapOverlayControlsProps {
  filters: OverlayFilters;
  onFilterChange: (filters: OverlayFilters) => void;
}

const ENTITY_TYPE_OPTIONS: { value: EntityType; label: string }[] = [
  { value: "gate", label: "Gates" },
  { value: "entrance", label: "Entrances" },
  { value: "exit", label: "Exits" },
  { value: "escalator", label: "Escalators" },
  { value: "elevator", label: "Elevators" },
  { value: "restroom", label: "Restrooms" },
  { value: "medical_room", label: "Medical" },
  { value: "food_court", label: "Food Courts" },
  { value: "security_checkpoint", label: "Security" },
  { value: "camera", label: "Cameras" },
  { value: "aed", label: "AEDs" },
  { value: "emergency_exit", label: "Emergency Exits" },
  { value: "volunteer_position", label: "Volunteers" },
  { value: "information_desk", label: "Info Desks" },
];

function MapOverlayControlsInner({ filters, onFilterChange }: MapOverlayControlsProps) {
  const toggleEntityType = useCallback(
    (type: EntityType) => {
      const current = filters.entityTypes;
      const updated = current.includes(type)
        ? current.filter((t) => t !== type)
        : [...current, type];
      onFilterChange({ ...filters, entityTypes: updated });
    },
    [filters, onFilterChange],
  );

  const toggleOverlay = useCallback(
    (key: keyof Pick<OverlayFilters, "accessibilityOverlay" | "emergencyOverlay" | "crowdOverlay">) => {
      onFilterChange({ ...filters, [key]: !filters[key] });
    },
    [filters, onFilterChange],
  );

  return (
    <div className="absolute left-4 top-4 z-30 bg-gray-900/90 backdrop-blur-sm rounded-lg border border-gray-800 p-3 w-56">
      <h3 className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-2">
        Filters
      </h3>

      {/* Entity type toggles */}
      <div className="flex flex-wrap gap-1 mb-3">
        {ENTITY_TYPE_OPTIONS.map(({ value, label }) => (
          <button
            key={value}
            type="button"
            onClick={() => toggleEntityType(value)}
            className={`
              text-[10px] px-1.5 py-0.5 rounded border transition-colors
              ${
                filters.entityTypes.includes(value)
                  ? "bg-blue-600 border-blue-500 text-white"
                  : "bg-gray-800 border-gray-700 text-gray-400 hover:text-white"
              }
            `}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Overlay toggles */}
      <h3 className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-2">
        Overlays
      </h3>
      <div className="space-y-1">
        {[
          { key: "accessibilityOverlay" as const, label: "Accessibility", color: "bg-blue-500" },
          { key: "emergencyOverlay" as const, label: "Emergency", color: "bg-red-500" },
          { key: "crowdOverlay" as const, label: "Crowd Density", color: "bg-amber-500" },
        ].map(({ key, label, color }) => (
          <button
            key={key}
            type="button"
            onClick={() => toggleOverlay(key)}
            className={`
              flex items-center gap-2 w-full text-sm px-2 py-1 rounded transition-colors
              ${filters[key] ? "bg-gray-800 text-white" : "text-gray-500 hover:text-gray-300"}
            `}
          >
            <span className={`w-2 h-2 rounded-full ${filters[key] ? color : "bg-gray-600"}`} />
            {label}
          </button>
        ))}
      </div>
    </div>
  );
}

export const MapOverlayControls = memo(MapOverlayControlsInner);
