/**
 * Color mappings for operational status and entity health.
 * Used by all digital twin map components for consistent visual language.
 */

import type { EntityType, OperationalStatus, EntityHealth } from "@/types/digital-twin";

/** Operational status -> Tailwind color class (dark mode). */
export const STATUS_COLORS: Record<OperationalStatus, string> = {
  operational: "bg-emerald-500",
  degraded: "bg-amber-500",
  maintenance: "bg-blue-500",
  offline: "bg-gray-500",
  emergency: "bg-red-600",
  closed: "bg-gray-700",
  temporary_closure: "bg-orange-500",
};

/** Entity health -> border ring color. */
export const HEALTH_COLORS: Record<EntityHealth, string> = {
  healthy: "ring-emerald-400",
  warning: "ring-amber-400",
  critical: "ring-red-500",
  unknown: "ring-gray-400",
};

/** Entity type -> display icon label. */
export const ENTITY_ICONS: Record<EntityType, string> = {
  gate: "Gate",
  entrance: "Entrance",
  exit: "Exit",
  zone: "Zone",
  concourse: "Corridor",
  corridor: "Corridor",
  escalator: "Escalator",
  elevator: "Elevator",
  ramp: "Ramp",
  staircase: "Stairs",
  restroom: "Restroom",
  medical_room: "Medical",
  food_court: "Food",
  vendor: "Vendor",
  security_checkpoint: "Security",
  parking_area: "Parking",
  metro_station: "Metro",
  bus_stop: "Bus",
  shuttle_point: "Shuttle",
  camera: "Camera",
  iot_sensor: "Sensor",
  volunteer_position: "Volunteer",
  crowd_cluster: "Crowd",
  emergency_exit: "Emergency",
  fire_extinguisher: "Fire",
  aed: "AED",
  wheelchair_station: "Wheelchair",
  cleaning_bin: "Bin",
  charging_station: "Charging",
  lost_and_found: "Lost",
  information_desk: "Info",
  seating_block: "Seating",
  seating_row: "Row",
  seat: "Seat",
  concession_stand: "Concession",
  first_aid_post: "First Aid",
  command_center: "Command",
  press_box: "Press",
  vip_lounge: "VIP",
  luxury_box: "Luxury",
  field: "Field",
  stage: "Stage",
  barrier: "Barrier",
  signage: "Sign",
  lighting: "Light",
  speaker: "Speaker",
  display_screen: "Screen",
  water_fountain: "Water",
  wifi_access_point: "WiFi",
};

/** Capacity percentage thresholds for color coding. */
export function getCapacityColor(current: number, max: number): string {
  if (max === 0) return "text-gray-400";
  const pct = (current / max) * 100;
  if (pct >= 90) return "text-red-500";
  if (pct >= 70) return "text-amber-500";
  return "text-emerald-500";
}
