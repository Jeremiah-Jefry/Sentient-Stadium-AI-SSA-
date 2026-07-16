/**
 * Shared TypeScript types for the IAM module.
 * Mirrors the backend DTOs for type safety across the stack.
 */

export type AuthProvider = "email_password" | "google" | "firebase";

export type UserStatus =
  | "active"
  | "inactive"
  | "suspended"
  | "pending_verification"
  | "locked";

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface UserSummary {
  id: string;
  email: string;
  display_name: string;
  photo_url: string | null;
  email_verified: boolean;
  auth_provider: AuthProvider;
  status: UserStatus;
}

export interface AuthResponse {
  tokens: TokenPair;
  user: UserSummary;
}

export interface RoleSummary {
  id: string;
  name: string;
  display_name: string;
  scope: string;
}

export interface PermissionSummary {
  id: string;
  name: string;
  resource: string;
  action: string;
}

export interface UserProfile {
  id: string;
  email: string;
  display_name: string;
  photo_url: string | null;
  phone_number: string | null;
  auth_provider: AuthProvider;
  email_verified: boolean;
  status: UserStatus;
  roles: RoleSummary[];
  created_at: string;
  updated_at: string;
  last_login_at: string | null;
}

export interface SessionInfo {
  id: string;
  device_info: Record<string, unknown> | null;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
  last_active_at: string;
  is_current: boolean;
}

export interface AuditLogEntry {
  id: string;
  event_type: string;
  ip_address: string | null;
  resource_type: string | null;
  resource_id: string | null;
  details: Record<string, unknown> | null;
  risk_score: number | null;
  created_at: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ApiError {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
}
