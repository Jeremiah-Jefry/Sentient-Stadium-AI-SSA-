/**
 * Typed API client for the StadiumMind Digital Twin backend.
 *
 * Handles entity CRUD, spatial queries, pathfinding, and zone management.
 * Uses the shared api-client infrastructure for auth token injection.
 */

import type {
  Entity,
  EntitySummary,
  EntityEvent,
  EntityVersion,
  PaginatedEntityResponse,
  Venue,
  Zone,
  ZoneTree,
  GraphEdge,
  NearbySearchResponse,
  PathfindingResponse,
} from "@/types/digital-twin";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

const REQUEST_TIMEOUT_MS = 30_000;

let accessToken: string | null = null;

export function setDigitalTwinToken(token: string | null): void {
  accessToken = token;
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({
      error: { code: "UNKNOWN_ERROR", message: `HTTP ${response.status}` },
    }));
    throw new Error(errorBody.error?.message ?? `Request failed: ${response.status}`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

interface RequestOptions {
  method?: string;
  body?: unknown;
}

async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body } = options;
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (accessToken) headers["Authorization"] = `Bearer ${accessToken}`;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });
    return await handleResponse<T>(response);
  } finally {
    clearTimeout(timeoutId);
  }
}

// Entity API
export const entityApi = {
  create: (data: Record<string, unknown>) =>
    apiRequest<Entity>("/entities/", { method: "POST", body: data }),

  get: (id: string) =>
    apiRequest<Entity>(`/entities/${id}`),

  update: (id: string, data: Record<string, unknown>) =>
    apiRequest<Entity>(`/entities/${id}`, { method: "PUT", body: data }),

  updateState: (id: string, data: Record<string, unknown>) =>
    apiRequest<void>(`/entities/${id}/state`, { method: "PATCH", body: data }),

  search: (params: Record<string, string | number>) => {
    const qs = new URLSearchParams(
      Object.entries(params)
        .filter(([, v]) => v !== undefined && v !== null && v !== "")
        .map(([k, v]) => [k, String(v)]),
    ).toString();
    return apiRequest<PaginatedEntityResponse>(`/entities/search?${qs}`);
  },

  delete: (id: string) =>
    apiRequest<void>(`/entities/${id}`, { method: "DELETE" }),

  getEvents: (id: string, page = 1, pageSize = 50) =>
    apiRequest<{ events: EntityEvent[]; total: number }>(
      `/entities/${id}/events?page=${page}&page_size=${pageSize}`,
    ),

  bulkUpdateState: (data: Record<string, unknown>) =>
    apiRequest<{ updated_count: number; failed_ids: string[] }>(
      "/entities/bulk/state",
      { method: "POST", body: data },
    ),
};

// Venue API
export const venueApi = {
  list: () =>
    apiRequest<{ items: Venue[]; total: number }>("/venues/"),

  get: (id: string) =>
    apiRequest<Venue>(`/venues/${id}`),

  create: (data: Record<string, unknown>) =>
    apiRequest<Venue>("/venues/", { method: "POST", body: data }),

  getZoneTree: (venueId: string) =>
    apiRequest<ZoneTree[]>(`/venues/${venueId}/zones/tree`),

  createZone: (venueId: string, data: Record<string, unknown>) =>
    apiRequest<Zone>(`/venues/${venueId}/zones`, { method: "POST", body: data }),
};

// Spatial API
export const spatialApi = {
  nearby: (params: {
    latitude: number;
    longitude: number;
    radius_meters?: number;
    entity_type?: string;
    limit?: number;
  }) => {
    const qs = new URLSearchParams(
      Object.entries(params)
        .filter(([, v]) => v !== undefined && v !== null)
        .map(([k, v]) => [k, String(v)]),
    ).toString();
    return apiRequest<NearbySearchResponse>(`/spatial/nearby?${qs}`);
  },

  findPath: (data: {
    from_entity_id: string;
    to_entity_id: string;
    accessibility_level?: string;
    edge_type?: string;
  }) => apiRequest<PathfindingResponse>("/spatial/pathfinding", { method: "POST", body: data }),

  createEdge: (data: Record<string, unknown>) =>
    apiRequest<GraphEdge>("/spatial/edges", { method: "POST", body: data }),

  getEdges: (venueId: string) =>
    apiRequest<GraphEdge[]>(`/spatial/edges/${venueId}`),
};
