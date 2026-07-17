/**
 * Shared TypeScript types for the Digital Twin module.
 * Mirrors the backend DTOs for type safety across the full stack.
 */

export type EntityType =
  | "gate"
  | "entrance"
  | "exit"
  | "zone"
  | "concourse"
  | "corridor"
  | "escalator"
  | "elevator"
  | "ramp"
  | "staircase"
  | "restroom"
  | "medical_room"
  | "food_court"
  | "vendor"
  | "security_checkpoint"
  | "parking_area"
  | "metro_station"
  | "bus_stop"
  | "shuttle_point"
  | "camera"
  | "iot_sensor"
  | "volunteer_position"
  | "crowd_cluster"
  | "emergency_exit"
  | "fire_extinguisher"
  | "aed"
  | "wheelchair_station"
  | "cleaning_bin"
  | "charging_station"
  | "lost_and_found"
  | "information_desk"
  | "seating_block"
  | "seating_row"
  | "seat"
  | "concession_stand"
  | "first_aid_post"
  | "command_center"
  | "press_box"
  | "vip_lounge"
  | "luxury_box"
  | "field"
  | "stage"
  | "barrier"
  | "signage"
  | "lighting"
  | "speaker"
  | "display_screen"
  | "water_fountain"
  | "wifi_access_point";

export type OperationalStatus =
  | "operational"
  | "degraded"
  | "maintenance"
  | "offline"
  | "emergency"
  | "closed"
  | "temporary_closure";

export type EntityHealth = "healthy" | "warning" | "critical" | "unknown";

export type AccessibilityLevel = "full" | "partial" | "none";

export type ZoneType =
  | "stadium"
  | "sector"
  | "zone"
  | "sub_zone"
  | "gate"
  | "checkpoint"
  | "node"
  | "floor"
  | "level"
  | "section"
  | "area";

export type EdgeType =
  | "walking"
  | "wheelchair"
  | "emergency"
  | "staff_only"
  | "restricted"
  | "maintenance";

export interface EntityComponent {
  component_type: string;
  component_data: Record<string, unknown>;
}

export interface Entity {
  id: string;
  name: string;
  description: string | null;
  entity_type: EntityType;
  operational_status: OperationalStatus;
  current_health: EntityHealth;
  current_capacity: number;
  max_capacity: number;
  coordinates_lat: number;
  coordinates_lon: number;
  indoor_x: number | null;
  indoor_y: number | null;
  floor_number: number | null;
  building_level: number | null;
  accessibility_level: AccessibilityLevel;
  accessibility_metadata: Record<string, unknown> | null;
  current_state: Record<string, unknown> | null;
  metadata_json: Record<string, unknown> | null;
  venue_id: string;
  zone_id: string | null;
  parent_id: string | null;
  components: EntityComponent[];
  created_at: string;
  updated_at: string;
}

export interface EntitySummary {
  id: string;
  name: string;
  entity_type: EntityType;
  operational_status: OperationalStatus;
  current_health: EntityHealth;
  current_capacity: number;
  max_capacity: number;
  coordinates_lat: number;
  coordinates_lon: number;
  zone_id: string | null;
}

export interface PaginatedEntityResponse {
  items: EntitySummary[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface Venue {
  id: string;
  name: string;
  description: string | null;
  address: string | null;
  coordinates_lat: number;
  coordinates_lon: number;
  timezone: string;
  metadata_json: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface Zone {
  id: string;
  name: string;
  description: string | null;
  zone_type: ZoneType;
  level: number;
  parent_zone_id: string | null;
  venue_id: string;
  bounds_lat_min: number | null;
  bounds_lat_max: number | null;
  bounds_lon_min: number | null;
  bounds_lon_max: number | null;
  metadata_json: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface ZoneTree extends Omit<Zone, "created_at" | "updated_at"> {
  children: ZoneTree[];
}

export interface GraphEdge {
  id: string;
  from_entity_id: string;
  to_entity_id: string;
  edge_type: EdgeType;
  weight: number;
  is_bidirectional: boolean;
  accessibility_level: AccessibilityLevel;
  venue_id: string;
}

export interface NearbyEntity extends EntitySummary {
  distance_meters: number;
}

export interface NearbySearchResponse {
  entities: NearbyEntity[];
  query_lat: number;
  query_lon: number;
  radius_meters: number;
  count: number;
}

export interface PathStep {
  entity_id: string;
  entity_name: string;
  entity_type: EntityType;
  coordinates_lat: number;
  coordinates_lon: number;
  edge_type: string;
  distance_meters: number;
}

export interface PathfindingResponse {
  from_entity_id: string;
  to_entity_id: string;
  steps: PathStep[];
  total_distance_meters: number;
  total_steps: number;
  accessibility_compliant: boolean;
}

export interface EntityEvent {
  id: string;
  entity_id: string;
  event_type: string;
  event_data: Record<string, unknown> | null;
  source: string;
  created_at: string;
}

export interface EntityVersion {
  id: string;
  version: number;
  state_snapshot: Record<string, unknown>;
  changed_by: string | null;
  change_reason: string | null;
  created_at: string;
}

export interface WebSocketMessage {
  action: "subscribe_venue" | "subscribe_entity" | "unsubscribe_venue" | "unsubscribe_entity";
  venue_id?: string;
  entity_id?: string;
}

export interface WebSocketEvent {
  event_type: string;
  entity_id: string;
  entity_name?: string;
  data: Record<string, unknown>;
  timestamp: string;
}
