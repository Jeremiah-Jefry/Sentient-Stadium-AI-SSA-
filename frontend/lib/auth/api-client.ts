/**
 * Typed API client for communicating with the StadiumMind IAM backend.
 *
 * Handles token injection, refresh rotation, and structured error responses.
 * Uses native fetch with proper timeout and abort signal support.
 */

import type {
  ApiError,
  AuthResponse,
  PaginatedResponse,
  TokenPair,
  UserProfile,
  AuditLogEntry,
  SessionInfo,
} from "@/types/auth";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

const REQUEST_TIMEOUT_MS = 30_000;

let accessToken: string | null = null;
let refreshToken: string | null = null;

export function setTokens(access: string, refresh: string): void {
  accessToken = access;
  refreshToken = refresh;
  if (typeof window !== "undefined") {
    localStorage.setItem("sm_refresh_token", refresh);
  }
}

export function clearTokens(): void {
  accessToken = null;
  refreshToken = null;
  if (typeof window !== "undefined") {
    localStorage.removeItem("sm_refresh_token");
  }
}

export function loadRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("sm_refresh_token");
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const errorBody: ApiError = await response.json().catch(() => ({
      error: {
        code: "UNKNOWN_ERROR",
        message: `HTTP ${response.status}`,
      },
    }));

    if (response.status === 401 && errorBody.error.code === "TOKEN_EXPIRED") {
      const refreshed = await attemptTokenRefresh();
      if (refreshed) {
        throw new Error("TOKEN_REFRESHED_RETRY");
      }
    }

    throw new Error(errorBody.error.message || `Request failed: ${response.status}`);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

async function attemptTokenRefresh(): Promise<boolean> {
  const storedRefresh = refreshToken ?? loadRefreshToken();
  if (!storedRefresh) return false;

  try {
    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: storedRefresh }),
    });

    if (!response.ok) return false;

    const data: TokenPair = await response.json();
    setTokens(data.access_token, data.refresh_token);
    return true;
  } catch {
    clearTokens();
    return false;
  }
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  requireAuth?: boolean;
}

async function apiRequest<T>(
  path: string,
  options: RequestOptions = {}
): Promise<T> {
  const { method = "POST", body, requireAuth = true } = options;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (requireAuth && accessToken) {
    headers["Authorization"] = `Bearer ${accessToken}`;
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });

    return await handleResponse<T>(response);
  } catch (error) {
    if (error instanceof Error && error.message === "TOKEN_REFRESHED_RETRY") {
      headers["Authorization"] = `Bearer ${accessToken}`;
      const retryResponse = await fetch(`${API_BASE_URL}${path}`, {
        method,
        headers,
        body: body ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });
      return handleResponse<T>(retryResponse);
    }
    throw error;
  } finally {
    clearTimeout(timeoutId);
  }
}

// Auth API
export const authApi = {
  register: (data: {
    email: string;
    password: string;
    display_name: string;
  }) => apiRequest<AuthResponse>("/auth/register", { body: data, requireAuth: false }),

  loginFirebase: (data: { id_token: string; fingerprint: string }) =>
    apiRequest<AuthResponse>("/auth/login/firebase", { body: data, requireAuth: false }),

  loginGoogle: (data: {
    access_token: string;
    fingerprint: string;
  }) => apiRequest<AuthResponse>("/auth/login/google", { body: data, requireAuth: false }),

  refresh: (data: { refresh_token: string }) =>
    apiRequest<TokenPair>("/auth/refresh", { body: data, requireAuth: false }),

  logout: (data: { refresh_token?: string; all_devices?: boolean }) =>
    apiRequest<{ message: string; sessions_revoked: number }>(
      "/auth/logout",
      { body: data, requireAuth: true }
    ),

  resetPassword: (data: { email: string }) =>
    apiRequest<{ message: string }>(
      "/auth/password/reset",
      { body: data, requireAuth: false }
    ),
};

// User API
export const userApi = {
  getProfile: () => apiRequest<UserProfile>("/users/me", { method: "GET" }),

  getSessions: () =>
    apiRequest<SessionInfo[]>("/users/me/sessions", { method: "GET" }),

  revokeSession: (sessionId: string) =>
    apiRequest<void>(`/users/me/sessions/${sessionId}`, { method: "DELETE" }),

  getAuditLog: (page = 1, pageSize = 50) =>
    apiRequest<PaginatedResponse<AuditLogEntry>>(
      `/users/me/audit-log?page=${page}&page_size=${pageSize}`,
      { method: "GET" }
    ),
};
