/**
 * Digital Twin dashboard page - Interactive stadium visualization.
 *
 * Protected route that renders the full digital twin map with
 * real-time entity monitoring, filtering, and detail inspection.
 */

"use client";

import { useAuth } from "@/hooks/use-auth";
import { ProtectedRoute } from "@/components/auth/protected-route";
import { DigitalTwinMap } from "@/components/digital-twin";

const DEMO_VENUE_ID = "00000000-0000-0000-0000-000000000001";

function DigitalTwinContent() {
  const { user } = useAuth();

  return (
    <div className="h-screen flex flex-col bg-gray-950">
      {/* Header */}
      <header className="h-14 border-b border-gray-800 flex items-center justify-between px-6 shrink-0">
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-semibold text-white">Digital Twin</h1>
          <span className="text-xs text-gray-500 bg-gray-800 px-2 py-0.5 rounded">
            Live
          </span>
        </div>
        <div className="flex items-center gap-4 text-sm text-gray-400">
          <span>{user?.display_name ?? "Operator"}</span>
        </div>
      </header>

      {/* Map */}
      <main className="flex-1 p-2">
        <DigitalTwinMap venueId={DEMO_VENUE_ID} />
      </main>
    </div>
  );
}

export default function DigitalTwinPage() {
  return (
    <ProtectedRoute>
      <DigitalTwinContent />
    </ProtectedRoute>
  );
}
