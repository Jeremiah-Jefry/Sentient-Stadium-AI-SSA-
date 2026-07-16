/**
 * useRBAC hook - Role-Based Access Control checks for UI components.
 */

"use client";

import { useMemo } from "react";
import { useAuth } from "./use-auth";

export interface RBACContext {
  hasRole: (role: string) => boolean;
  hasPermission: (permission: string) => boolean;
  hasAnyRole: (roles: string[]) => boolean;
  hasAnyPermission: (permissions: string[]) => boolean;
  isAdmin: boolean;
  isVolunteer: boolean;
  isSecurityOfficer: boolean;
  isOperationsManager: boolean;
}

export function useRBAC(): RBACContext {
  const { profile } = useAuth();

  return useMemo(() => {
    const roleNames = profile?.roles?.map((r) => r.name) ?? [];

    const hasRole = (role: string): boolean => roleNames.includes(role);

    const hasPermission = (_permission: string): boolean => {
      // Permissions are resolved server-side from roles.
      // For client-side guards, use role-based checks.
      return hasRole("admin");
    };

    const hasAnyRole = (roles: string[]): boolean =>
      roles.some((r) => hasRole(r));

    const hasAnyPermission = (permissions: string[]): boolean =>
      permissions.some((p) => hasPermission(p));

    return {
      hasRole,
      hasPermission,
      hasAnyRole,
      hasAnyPermission,
      isAdmin: hasRole("admin"),
      isVolunteer: hasRole("volunteer"),
      isSecurityOfficer: hasRole("security_officer"),
      isOperationsManager: hasRole("operations_manager"),
    };
  }, [profile]);
}
