/**
 * RoleGuard - renders children only if the user has the required role.
 *
 * Shows an unauthorized message when the user lacks the role.
 * Useful for admin-only sections and role-specific UI.
 */

"use client";

import { useRBAC } from "@/hooks/use-rbac";

interface RoleGuardProps {
  role: string;
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

export function RoleGuard({ role, children, fallback }: RoleGuardProps) {
  const { hasRole } = useRBAC();

  if (!hasRole(role)) {
    return (
      fallback ?? (
        <div className="flex min-h-[200px] items-center justify-center rounded-lg border border-dashed border-destructive/30 bg-destructive/5 p-8">
          <div className="text-center">
            <p className="text-lg font-semibold text-destructive">
              Access Denied
            </p>
            <p className="mt-2 text-sm text-muted-foreground">
              You need the &quot;{role}&quot; role to view this content.
            </p>
          </div>
        </div>
      )
    );
  }

  return <>{children}</>;
}

interface MultiRoleGuardProps {
  roles: string[];
  requireAll?: boolean;
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

export function MultiRoleGuard({
  roles,
  requireAll = false,
  children,
  fallback,
}: MultiRoleGuardProps) {
  const { hasAnyRole } = useRBAC();

  if (!hasAnyRole(roles)) {
    return (
      fallback ?? (
        <div className="flex min-h-[200px] items-center justify-center rounded-lg border border-dashed border-destructive/30 bg-destructive/5 p-8">
          <div className="text-center">
            <p className="text-lg font-semibold text-destructive">
              Access Denied
            </p>
            <p className="mt-2 text-sm text-muted-foreground">
              You need one of the following roles: {roles.join(", ")}
            </p>
          </div>
        </div>
      )
    );
  }

  return <>{children}</>;
}
