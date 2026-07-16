/**
 * Authentication context providing global auth state management.
 *
 * Wraps Firebase Auth state with backend token management.
 * Provides user state, login/logout actions, and token refresh
 * to all components in the tree.
 */

"use client";

import {
  createContext,
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { onAuthStateChanged, type User as FirebaseUser } from "firebase/auth";
import { getFirebaseAuth } from "@/lib/firebase/config";
import {
  signInWithEmail,
  signInWithGoogle,
  signUpWithEmail,
  signOutUser,
  resetPassword as fbResetPassword,
} from "@/lib/firebase/auth";
import { authApi, setTokens, clearTokens } from "@/lib/auth/api-client";
import type { UserProfile, AuthResponse } from "@/types/auth";

export interface AuthContextValue {
  user: FirebaseUser | null;
  profile: UserProfile | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  loginWithEmail: (email: string, password: string) => Promise<void>;
  loginWithGoogle: () => Promise<void>;
  register: (
    email: string,
    password: string,
    displayName: string
  ) => Promise<void>;
  logout: () => Promise<void>;
  resetPassword: (email: string) => Promise<void>;
  refreshProfile: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<FirebaseUser | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const handleAuthResult = useCallback(
    async (authResponse: AuthResponse) => {
      setTokens(authResponse.tokens.access_token, authResponse.tokens.refresh_token);
      setProfile(authResponse.user as unknown as UserProfile);
    },
    []
  );

  const refreshProfile = useCallback(async () => {
    try {
      const { userApi } = await import("@/lib/auth/api-client");
      const userProfile = await userApi.getProfile();
      setProfile(userProfile);
    } catch {
      // Profile fetch failed silently - user state remains from login
    }
  }, []);

  useEffect(() => {
    const auth = getFirebaseAuth();
    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
      setUser(firebaseUser);
      if (!firebaseUser) {
        clearTokens();
        setProfile(null);
      }
      setIsLoading(false);
    });

    return () => unsubscribe();
  }, []);

  const loginWithEmail = useCallback(
    async (email: string, password: string) => {
      const result = await signInWithEmail(email, password);
      const fingerprint = await generateFingerprint();
      const apiResult = await authApi.loginFirebase({
        id_token: result.idToken,
        fingerprint,
      });
      await handleAuthResult(apiResult);
    },
    [handleAuthResult]
  );

  const loginWithGoogle = useCallback(async () => {
    const result = await signInWithGoogle();
    const fingerprint = await generateFingerprint();
    const apiResult = await authApi.loginGoogle({
      access_token: result.idToken,
      fingerprint,
    });
    await handleAuthResult(apiResult);
  }, [handleAuthResult]);

  const register = useCallback(
    async (email: string, password: string, displayName: string) => {
      const apiResult = await authApi.register({
        email,
        password,
        display_name: displayName,
      });
      await handleAuthResult(apiResult);
    },
    [handleAuthResult]
  );

  const logout = useCallback(async () => {
    try {
      await authApi.logout({ all_devices: false });
    } catch {
      // Logout API failed - still sign out locally
    }
    await signOutUser();
    clearTokens();
    setProfile(null);
  }, []);

  const resetPassword = useCallback(async (email: string) => {
    await fbResetPassword(email);
  }, []);

  const value: AuthContextValue = useMemo(
    () => ({
      user,
      profile,
      isLoading,
      isAuthenticated: !!user && !!profile,
      loginWithEmail,
      loginWithGoogle,
      register,
      logout,
      resetPassword,
      refreshProfile,
    }),
    [
      user,
      profile,
      isLoading,
      loginWithEmail,
      loginWithGoogle,
      register,
      logout,
      resetPassword,
      refreshProfile,
    ]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

async function generateFingerprint(): Promise<string> {
  const canvas = document.createElement("canvas");
  const ctx = canvas.getContext("2d");
  if (!ctx) return "fallback";

  ctx.textBaseline = "top";
  ctx.font = "14px 'Arial'";
  ctx.fillStyle = "#f60";
  ctx.fillRect(125, 1, 62, 20);
  ctx.fillStyle = "#069";
  ctx.fillText("StadiumMind", 2, 15);

  const data = canvas.toDataURL();
  const encoder = new TextEncoder();
  const dataBuffer = encoder.encode(data);
  const hashBuffer = await crypto.subtle.digest("SHA-256", dataBuffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
}
