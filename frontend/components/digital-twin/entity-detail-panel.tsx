/**
 * EntityDetailPanel - Slide-out panel showing full entity details.
 *
 * Displays complete entity state, capacity, health, components,
 * accessibility info, and recent events.
 */

"use client";

import { memo } from "react";

import { STATUS_COLORS, HEALTH_COLORS, ENTITY_ICONS, getCapacityColor } from "./constants";
import type { Entity, EntityEvent } from "@/types/digital-twin";

interface EntityDetailPanelProps {
  entity: Entity | null;
  events: EntityEvent[];
  onClose: () => void;
  isLoading: boolean;
}

function EntityDetailPanelInner({
  entity,
  events,
  onClose,
  isLoading,
}: EntityDetailPanelProps) {
  if (!entity) return null;

  const capacityPct =
    entity.max_capacity > 0
      ? Math.round((entity.current_capacity / entity.max_capacity) * 100)
      : 0;

  const statusColor = STATUS_COLORS[entity.operational_status];
  const healthRing = HEALTH_COLORS[entity.current_health];
  const capacityTextColor = getCapacityColor(
    entity.current_capacity,
    entity.max_capacity,
  );

  return (
    <aside
      className="fixed right-0 top-0 h-full w-96 bg-gray-900 border-l border-gray-800 overflow-y-auto z-40 shadow-2xl"
      role="complementary"
      aria-label="Entity details"
    >
      {/* Header */}
      <div className="sticky top-0 bg-gray-900 border-b border-gray-800 p-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={`w-3 h-3 rounded-full ${statusColor} ring-2 ${healthRing}`} />
          <h2 className="text-lg font-semibold text-white">{entity.name}</h2>
        </div>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-white transition-colors"
          aria-label="Close panel"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {isLoading ? (
        <div className="p-4 text-gray-500 text-center">Loading...</div>
      ) : (
        <div className="p-4 space-y-6">
          {/* Type & Status */}
          <section>
            <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Status</h3>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div className="bg-gray-800 rounded p-2">
                <span className="text-gray-400">Type</span>
                <p className="text-white font-medium">{ENTITY_ICONS[entity.entity_type]}</p>
              </div>
              <div className="bg-gray-800 rounded p-2">
                <span className="text-gray-400">Status</span>
                <p className="text-white font-medium capitalize">{entity.operational_status}</p>
              </div>
              <div className="bg-gray-800 rounded p-2">
                <span className="text-gray-400">Health</span>
                <p className="text-white font-medium capitalize">{entity.current_health}</p>
              </div>
              <div className="bg-gray-800 rounded p-2">
                <span className="text-gray-400">Access</span>
                <p className="text-white font-medium capitalize">{entity.accessibility_level}</p>
              </div>
            </div>
          </section>

          {/* Capacity */}
          <section>
            <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Capacity</h3>
            <div className="bg-gray-800 rounded p-3">
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm text-gray-400">
                  {entity.current_capacity} / {entity.max_capacity}
                </span>
                <span className={`text-sm font-semibold ${capacityTextColor}`}>
                  {capacityPct}%
                </span>
              </div>
              <div className="w-full h-2 bg-gray-700 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-300 ${STATUS_COLORS[entity.operational_status]}`}
                  style={{ width: `${capacityPct}%` }}
                />
              </div>
            </div>
          </section>

          {/* Coordinates */}
          <section>
            <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Location</h3>
            <div className="bg-gray-800 rounded p-3 text-sm space-y-1">
              <div className="flex justify-between">
                <span className="text-gray-400">Latitude</span>
                <span className="text-white">{entity.coordinates_lat.toFixed(7)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Longitude</span>
                <span className="text-white">{entity.coordinates_lon.toFixed(7)}</span>
              </div>
              {entity.floor_number !== null && (
                <div className="flex justify-between">
                  <span className="text-gray-400">Floor</span>
                  <span className="text-white">{entity.floor_number}</span>
                </div>
              )}
            </div>
          </section>

          {/* Recent Events */}
          <section>
            <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Recent Events</h3>
            {events.length === 0 ? (
              <p className="text-sm text-gray-500">No recent events</p>
            ) : (
              <div className="space-y-2">
                {events.slice(0, 5).map((event) => (
                  <div key={event.id} className="bg-gray-800 rounded p-2 text-sm">
                    <div className="flex items-center justify-between">
                      <span className="text-white font-medium">{event.event_type}</span>
                      <span className="text-gray-500 text-xs">
                        {new Date(event.created_at).toLocaleTimeString()}
                      </span>
                    </div>
                    <span className="text-gray-400 text-xs">Source: {event.source}</span>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      )}
    </aside>
  );
}

export const EntityDetailPanel = memo(EntityDetailPanelInner);
