/**
 * Dashboard page - main application entry point after authentication.
 *
 * Protected by ProtectedRoute. Shows user info and role-based content.
 */

"use client";

import Link from "next/link";
import { ProtectedRoute } from "@/components/auth/protected-route";
import { useAuth } from "@/hooks/use-auth";
import { useRBAC } from "@/hooks/use-rbac";

function DashboardContent() {
  const { profile, logout } = useAuth();
  const rbac = useRBAC();

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div>
            <h1 className="text-lg font-semibold text-foreground">
              StadiumMind OS
            </h1>
            <p className="text-sm text-muted-foreground">
              Volunteer Co-Pilot Dashboard
            </p>
          </div>

          <div className="flex items-center gap-4">
            <div className="text-right">
              <p className="text-sm font-medium text-foreground">
                {profile?.display_name}
              </p>
              <p className="text-xs text-muted-foreground">
                {profile?.email}
              </p>
            </div>
            <button
              onClick={() => logout()}
              className="rounded-md border border-input px-3 py-1.5 text-sm text-muted-foreground hover:bg-accent"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-6 py-8">
        <div className="grid gap-6 md:grid-cols-3">
          <div className="rounded-lg border border-border bg-card p-6">
            <h2 className="text-sm font-medium text-muted-foreground">
              Role
            </h2>
            <p className="mt-2 text-2xl font-bold text-foreground">
              {profile?.roles?.[0]?.display_name ?? "Volunteer"}
            </p>
          </div>

          <div className="rounded-lg border border-border bg-card p-6">
            <h2 className="text-sm font-medium text-muted-foreground">
              Status
            </h2>
            <p className="mt-2 text-2xl font-bold text-foreground capitalize">
              {profile?.status ?? "active"}
            </p>
          </div>

          <div className="rounded-lg border border-border bg-card p-6">
            <h2 className="text-sm font-medium text-muted-foreground">
              Email Verified
            </h2>
            <p className="mt-2 text-2xl font-bold text-foreground">
              {profile?.email_verified ? "Yes" : "No"}
            </p>
          </div>
        </div>

        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <Link
            href="/orchestration"
            className="rounded-lg border border-indigo-500/30 bg-indigo-500/5 p-6 hover:border-indigo-500/50 transition-colors group"
          >
            <h2 className="text-lg font-semibold text-foreground group-hover:text-indigo-400 transition-colors">
              Orchestration Engine
            </h2>
            <p className="mt-2 text-sm text-muted-foreground">
              AI multi-agent orchestration, reasoning, and decision support.
            </p>
          </Link>

          <Link
            href="/orchestration/execute"
            className="rounded-lg border border-emerald-500/30 bg-emerald-500/5 p-6 hover:border-emerald-500/50 transition-colors group"
          >
            <h2 className="text-lg font-semibold text-foreground group-hover:text-emerald-400 transition-colors">
              Execute Request
            </h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Submit a request to the AI orchestration engine.
            </p>
          </Link>

          <Link
            href="/orchestration/agents"
            className="rounded-lg border border-purple-500/30 bg-purple-500/5 p-6 hover:border-purple-500/50 transition-colors group"
          >
            <h2 className="text-lg font-semibold text-foreground group-hover:text-purple-400 transition-colors">
              Agent Status
            </h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Monitor all AI agents and their health status.
            </p>
          </Link>
        </div>

        {rbac.isAdmin && (
          <div className="mt-8 rounded-lg border border-primary/30 bg-primary/5 p-6">
            <h2 className="text-lg font-semibold text-foreground">
              Admin Panel
            </h2>
            <p className="mt-2 text-sm text-muted-foreground">
              You have administrator access. User management features are available.
            </p>
          </div>
        )}

        {rbac.isSecurityOfficer && (
          <div className="mt-6 rounded-lg border border-yellow-500/30 bg-yellow-500/5 p-6">
            <h2 className="text-lg font-semibold text-foreground">
              Security Operations
            </h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Incident monitoring and security event review are available.
            </p>
          </div>
        )}
      </main>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <ProtectedRoute>
      <DashboardContent />
    </ProtectedRoute>
  );
}
