/**
 * DigitalTwinMap - Main map container for the stadium digital twin.
 *
 * Renders entities as interactive markers, supports real-time updates
 * via WebSocket, and provides overlay controls for filtering and
 * visualization layers.
 */

"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { entityApi, venueApi } from "@/lib/digital-twin/api-client";
import { useDigitalTwinWebSocket } from "@/hooks/use-digital-twin-ws";
import { EntityMarker } from "./entity-marker";
import { EntityDetailPanel } from "./entity-detail-panel";
import { MapOverlayControls } from "./map-overlay-controls";
import type {
  Entity,
  EntitySummary,
  EntityEvent,
  EntityType,
  OperationalStatus,
  EntityHealth,
  Venue,
} from "@/types/digital-twin";

interface DigitalTwinMapProps {
  venueId: string;
}

interface OverlayFilters {
  entityTypes: EntityType[];
  operationalStatus: OperationalStatus[];
  healthStatus: EntityHealth[];
  accessibilityOverlay: boolean;
  emergencyOverlay: boolean;
  crowdOverlay: boolean;
}

const INITIAL_FILTERS: OverlayFilters = {
  entityTypes: [],
  operationalStatus: [],
  healthStatus: [],
  accessibilityOverlay: false,
  emergencyOverlay: false,
  crowdOverlay: false,
};

export function DigitalTwinMap({ venueId }: DigitalTwinMapProps) {
  const [entities, setEntities] = useState<EntitySummary[]>([]);
  const [selectedEntity, setSelectedEntity] = useState<Entity | null>(null);
  const [selectedEvents, setSelectedEvents] = useState<EntityEvent[]>([]);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [filters, setFilters] = useState<OverlayFilters>(INITIAL_FILTERS);
  const [zoomLevel, setZoomLevel] = useState(2);
  const [isLoading, setIsLoading] = useState(true);
  const [isDetailLoading, setIsDetailLoading] = useState(false);

  // Load entities for the venue
  useEffect(() => {
    let cancelled = false;
    async function load() {
      setIsLoading(true);
      try {
        const result = await entityApi.search({ venue_id: venueId, page_size: 1000 });
        if (!cancelled) setEntities(result.items);
      } catch {
        // Silently handle - dashboard will show empty state
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [venueId]);

  // Real-time WebSocket updates
  const handleWsEvent = useCallback((event: { entity_id: string; event_type: string; data: Record<string, unknown> }) => {
    setEntities((prev) =>
      prev.map((e) => {
        if (e.id !== event.entity_id) return e;
        if (event.event_type === "state_changed" && event.data) {
          return {
            ...e,
            operational_status: (event.data.operational_status as OperationalStatus) ?? e.operational_status,
            current_health: (event.data.current_health as EntityHealth) ?? e.current_health,
            current_capacity: (event.data.current_capacity as number) ?? e.current_capacity,
          };
        }
        return e;
      }),
    );
    // Update detail panel if viewing the same entity
    if (selectedEntity?.id === event.entity_id) {
      setSelectedEntity((prev) => {
        if (!prev) return null;
        return { ...prev, ...event.data } as Entity;
      });
    }
  }, [selectedEntity?.id]);

  const { isConnected } = useDigitalTwinWebSocket({
    venueId,
    onEvent: handleWsEvent,
  });

  // Filter entities based on current overlay settings
  const filteredEntities = useMemo(() => {
    return entities.filter((e) => {
      if (filters.entityTypes.length > 0 && !filters.entityTypes.includes(e.entity_type)) return false;
      if (filters.operationalStatus.length > 0 && !filters.operationalStatus.includes(e.operational_status)) return false;
      if (filters.healthStatus.length > 0 && !filters.healthStatus.includes(e.current_health)) return false;
      return true;
    });
  }, [entities, filters]);

  // Entity selection handler
  const handleSelect = useCallback(async (entityId: string) => {
    setIsDetailLoading(true);
    try {
      const [entity, eventsResult] = await Promise.all([
        entityApi.get(entityId),
        entityApi.getEvents(entityId),
      ]);
      setSelectedEntity(entity);
      setSelectedEvents(eventsResult.events);
    } catch {
      // Handle silently
    } finally {
      setIsDetailLoading(false);
    }
  }, []);

  const handleClosePanel = useCallback(() => {
    setSelectedEntity(null);
    setSelectedEvents([]);
  }, []);

  return (
    <div className="relative w-full h-full bg-gray-950 rounded-lg overflow-hidden" role="region" aria-label="Digital Twin Map">
      {/* Map canvas */}
      <div className="absolute inset-0 bg-gray-900">
        {/* Grid pattern */}
        <svg className="absolute inset-0 w-full h-full opacity-10">
          <defs>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="currentColor" strokeWidth="0.5" className="text-gray-600" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />
        </svg>

        {/* Entity markers */}
        {filteredEntities.map((entity) => (
          <EntityMarker
            key={entity.id}
            entity={entity}
            isSelected={selectedEntity?.id === entity.id}
            onSelect={handleSelect}
            onHover={setHoveredId}
            zoomLevel={zoomLevel}
          />
        ))}
      </div>

      {/* Overlay controls */}
      <MapOverlayControls filters={filters} onFilterChange={setFilters} />

      {/* Connection status indicator */}
      <div className="absolute bottom-4 left-4 z-30 flex items-center gap-2 bg-gray-900/80 rounded px-2 py-1">
        <span className={`w-2 h-2 rounded-full ${isConnected ? "bg-emerald-500" : "bg-red-500"}`} />
        <span className="text-xs text-gray-400">
          {isConnected ? "Live" : "Disconnected"}
        </span>
        <span className="text-xs text-gray-600">
          {filteredEntities.length} entities
        </span>
      </div>

      {/* Zoom controls */}
      <div className="absolute bottom-4 right-4 z-30 flex flex-col gap-1">
        <button
          type="button"
          onClick={() => setZoomLevel((z) => Math.min(z + 1, 5))}
          className="w-8 h-8 bg-gray-900/80 rounded text-white hover:bg-gray-800 transition-colors flex items-center justify-center"
          aria-label="Zoom in"
        >
          +
        </button>
        <button
          type="button"
          onClick={() => setZoomLevel((z) => Math.max(z - 1, 1))}
          className="w-8 h-8 bg-gray-900/80 rounded text-white hover:bg-gray-800 transition-colors flex items-center justify-center"
          aria-label="Zoom out"
        >
          -
        </button>
      </div>

      {/* Detail panel */}
      <EntityDetailPanel
        entity={selectedEntity}
        events={selectedEvents}
        onClose={handleClosePanel}
        isLoading={isDetailLoading}
      />

      {/* Loading overlay */}
      {isLoading && (
        <div className="absolute inset-0 bg-gray-950/50 flex items-center justify-center z-50">
          <div className="text-gray-400 text-sm">Loading digital twin...</div>
        </div>
      )}
    </div>
  );
}
