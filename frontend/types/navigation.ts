/**
 * Shared TypeScript types for the Navigation Engine module.
 * Mirrors the backend DTOs for type safety across the full stack.
 */

export type RoutingProfile =
  | "spectator"
  | "volunteer"
  | "wheelchair_user"
  | "blind_user"
  | "hearing_impaired"
  | "medical_team"
  | "security_team"
  | "vip"
  | "maintenance_crew"
  | "cleaning_crew"
  | "administrator";

export type RouteType =
  | "fastest"
  | "safest"
  | "least_crowded"
  | "accessible"
  | "emergency"
  | "volunteer_assignment"
  | "medical_response"
  | "vip"
  | "maintenance"
  | "evacuation"
  | "delivery";

export type EmergencyType =
  | "fire"
  | "medical"
  | "evacuation"
  | "security"
  | "lost_child"
  | "crowd_crush"
  | "equipment_failure"
  | "chemical_hazard"
  | "power_outage"
  | "flooding";

export type SpatialQueryType =
  | "nearest_exit"
  | "nearest_aed"
  | "nearest_medical_room"
  | "nearest_volunteer"
  | "nearest_restroom"
  | "nearest_wheelchair_station"
  | "nearest_information_desk"
  | "nearest_security_officer"
  | "nearby_crowd_density"
  | "nearby_incidents"
  | "nearby_hazards"
  | "nearby_accessible_routes";

export type ReplanTrigger =
  | "gate_closure"
  | "crowd_surge"
  | "medical_incident"
  | "weather_change"
  | "security_restriction"
  | "infrastructure_failure"
  | "escalator_down"
  | "elevator_down"
  | "emergency_declared";

export interface RouteStep {
  node_id: string;
  name: string;
  entity_type: string;
  lat: number;
  lon: number;
  floor: number;
  edge_type: string;
  distance_meters: number;
}

export interface RouteResponse {
  route_id: string;
  origin_id: string;
  destination_id: string;
  steps: RouteStep[];
  total_distance_meters: number;
  total_time_seconds: number;
  safety_score: number;
  accessibility_score: number;
  crowd_exposure: number;
  confidence: number;
  grade: string;
  profile: string;
  route_type: string;
  computation_ms: number;
  algorithm_used: string;
}

export interface RouteExplanation {
  summary: string;
  why_selected: string;
  why_rejected_alternatives: string[];
  risk_factors: string[];
  expected_bottlenecks: string[];
  predicted_delays: string[];
  accessibility_notes: string[];
  tradeoffs: string[];
}

export interface RouteDetailResponse {
  route: RouteResponse;
  explanation: RouteExplanation;
  alternatives: RouteResponse[];
  simulation_success_probability: number;
  simulation_expected_delay: number;
  accessibility_valid: boolean;
  accessibility_violations: string[];
}

export interface EmergencyRouteResponse {
  route: RouteResponse;
  explanation: RouteExplanation;
  emergency_type: string;
}

export interface NearestEntityResponse {
  found: boolean;
  node_id?: string;
  name?: string;
  entity_type?: string;
  distance?: number;
  lat?: number;
  lon?: number;
}

export interface VolunteerAssignmentResponse {
  volunteer_id: string;
  task_id: string;
  travel_time_seconds: number;
  total_distance_meters: number;
  utility_score: number;
  reasoning: string;
}

export interface ReplanResponse {
  route_id: string;
  rerouted: boolean;
  trigger: string;
  reason: string;
}

export interface NavigationStatsResponse {
  graph_nodes: number;
  graph_edges: number;
  graph_version: number;
  active_routes: number;
  weight_engine: Record<string, unknown>;
}

export interface NavigationWSMessage {
  action: "subscribe_venue" | "unsubscribe_venue";
  venue_id?: string;
  token?: string;
}

export interface NavigationWSEvent {
  type: "route_update" | "replan_notification" | "congestion_alert" | "ping";
  venue_id: string;
  data: Record<string, unknown>;
  timestamp?: string;
}
