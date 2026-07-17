/**
 * NearestEntity - Display card for spatial query results.
 * Shows nearest entity with distance, type, and navigation prompt.
 */

"use client";

import { memo, useMemo } from "react";

import type { NearestEntityResponse } from "@/types/navigation";

interface NearestEntityProps {
  result: NearestEntityResponse;
  onNavigate?: (nodeId: string) => void;
}

const TYPE_ICONS: Record<string, string> = {
  exit: "EXIT",
  emergency_exit: "!! EXIT",
  aed: "AED",
  medical_room: "MED",
  first_aid_post: "MED",
  restroom: "WC",
  wheelchair_station: "ACCESS",
  information_desk: "INFO",
  security_checkpoint: "SEC",
  volunteer_position: "VOL",
};

function NearestEntityInner({ result, onNavigate }: NearestEntityProps) {
  const distDisplay = useMemo(() => {
    if (!result.distance) return "";
    return result.distance < 1000
      ? `${Math.round(result.distance)}m`
      : `${(result.distance / 1000).toFixed(1)}km`;
  }, [result.distance]);

  if (!result.found) {
    return (
      <div style={styles.notFound} role="status">
        No entity found nearby
      </div>
    );
  }

  const icon = TYPE_ICONS[result.entity_type ?? ""] ?? "LOC";

  return (
    <div style={styles.container} role="region" aria-label={`Nearest: ${result.name}`}>
      <div style={styles.iconBadge}>{icon}</div>
      <div style={styles.info}>
        <span style={styles.name}>{result.name}</span>
        <span style={styles.type}>{result.entity_type}</span>
      </div>
      <div style={styles.right}>
        <span style={styles.distance}>{distDisplay}</span>
        {onNavigate && result.node_id && (
          <button
            type="button"
            style={styles.navigateBtn}
            onClick={() => onNavigate(result.node_id!)}
            aria-label={`Navigate to ${result.name}`}
          >
            GO
          </button>
        )}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    padding: "8px 12px",
    backgroundColor: "#1e1e1e",
    borderRadius: 6,
    border: "1px solid #333",
  },
  notFound: {
    padding: "8px 12px",
    color: "#888",
    fontSize: 13,
    textAlign: "center",
  },
  iconBadge: {
    width: 40,
    height: 40,
    borderRadius: 6,
    backgroundColor: "#2d2d2d",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 9,
    fontWeight: 700,
    color: "#4caf50",
  },
  info: { flex: 1, display: "flex", flexDirection: "column", gap: 2 },
  name: { fontSize: 13, fontWeight: 600, color: "#e0e0e0" },
  type: { fontSize: 11, color: "#888" },
  right: { display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 4 },
  distance: { fontSize: 14, fontWeight: 700, color: "#2196f3" },
  navigateBtn: {
    padding: "2px 10px",
    fontSize: 11,
    fontWeight: 600,
    color: "#fff",
    backgroundColor: "#2196f3",
    border: "none",
    borderRadius: 4,
    cursor: "pointer",
  },
};

export const NearestEntity = memo(NearestEntityInner);
