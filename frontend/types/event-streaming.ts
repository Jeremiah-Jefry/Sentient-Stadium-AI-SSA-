/**
 * Shared TypeScript types for the Event Streaming module.
 * Mirrors the backend DTOs for type safety across the full stack.
 */

export type EventCategory =
  | "crowd"
  | "security"
  | "medical"
  | "transport"
  | "weather"
  | "infrastructure"
  | "operations"
  | "emergency"
  | "sensor"
  | "system";

export type SensorType =
  | "density_camera"
  | "thermal_camera"
  | "lidar"
  | "bluetooth_beacon"
  | "wifi_access_point"
  | "pressure_mat"
  | "gate_counter"
  | "air_quality"
  | "noise_level"
  | "temperature"
  | "humidity"
  | "wind_speed"
  | "rain_gauge"
  | "vibration"
  | "smoke_detector"
  | "gas_detector"
  | "radar";

export type EventPriority = "low" | "normal" | "high" | "critical";

export type EventSeverity =
  | "info"
  | "low"
  | "medium"
  | "high"
  | "critical"
  | "emergency";

export type ProcessingStatus =
  | "received"
  | "validating"
  | "deduplicating"
  | "normalizing"
  | "enriching"
  | "fusing"
  | "processed"
  | "failed"
  | "dead_lettered";

export type ConsumerStatus = "healthy" | "degraded" | "stopped" | "failed";

export interface StoredEvent {
  id: string;
  event_id: string;
  correlation_id: string | null;
  trace_id: string | null;
  parent_event_id: string | null;
  event_type: string;
  category: EventCategory;
  priority: EventPriority;
  severity: EventSeverity;
  source: string;
  producer: string;
  version: number;
  entity_id: string | null;
  venue_id: string | null;
  zone_id: string | null;
  payload: Record<string, unknown>;
  metadata_json: Record<string, unknown> | null;
  captured_at: string;
  processing_status: ProcessingStatus;
  retry_count: number;
  processing_duration_ms: number | null;
  created_at: string;
}

export interface EventSummary {
  id: string;
  event_id: string;
  event_type: string;
  category: EventCategory;
  severity: EventSeverity;
  producer: string;
  entity_id: string | null;
  captured_at: string;
  processing_status: ProcessingStatus;
}

export interface PaginatedEventResponse {
  items: EventSummary[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface BatchIngestResponse {
  accepted: number;
  rejected: number;
  event_ids: string[];
  errors: Array<{
    event_id: string;
    error_code: string;
    message: string;
  }>;
}

export interface StreamStatus {
  total_events_stored: number;
  events_per_second: number;
  avg_processing_latency_ms: number;
  active_consumers: number;
  dead_letter_count: number;
  pipeline_healthy: boolean;
  uptime_seconds: number;
}

export interface Sensor {
  id: string;
  name: string;
  description: string | null;
  sensor_type: SensorType;
  venue_id: string;
  entity_id: string | null;
  zone_id: string | null;
  coordinates_lat: number;
  coordinates_lon: number;
  indoor_x: number | null;
  indoor_y: number | null;
  floor_number: number | null;
  is_active: boolean;
  is_calibrated: boolean;
  last_calibration_at: string | null;
  reading_interval_ms: number;
  accuracy: number | null;
  range_meters: number | null;
  firmware_version: string | null;
  metadata_json: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface SensorHealth {
  total_sensors: number;
  active_sensors: number;
  inactive_sensors: number;
  calibrated_sensors: number;
  by_type: Record<string, { active: number; inactive: number }>;
}

export interface DeadLetterEvent {
  id: string;
  original_event_id: string;
  original_payload: Record<string, unknown>;
  error_type: string;
  error_message: string;
  retry_count: number;
  is_resolved: boolean;
  created_at: string;
}

export interface EventAggregation {
  id: string;
  venue_id: string;
  zone_id: string | null;
  window_type: string;
  window_start: string;
  window_end: string;
  event_count: number;
  events_by_category: Record<string, number>;
  events_by_severity: Record<string, number>;
  peak_crowd_density: number | null;
  avg_response_time_ms: number | null;
  anomalies_detected: number;
  alerts_triggered: number;
}

export interface FusedReading {
  value: number;
  confidence: number;
  algorithm: string;
  sensor_count: number;
}

export interface EventStreamMessage {
  action:
    | "subscribe_venue"
    | "subscribe_entity"
    | "subscribe_category"
    | "unsubscribe_venue"
    | "unsubscribe_entity"
    | "unsubscribe_category";
  venue_id?: string;
  entity_id?: string;
  category?: string;
}

export interface EventStreamEvent {
  event_type: string;
  category: EventCategory;
  severity: EventSeverity;
  entity_id: string | null;
  venue_id: string | null;
  data: Record<string, unknown>;
  timestamp: string;
  producer: string;
}
