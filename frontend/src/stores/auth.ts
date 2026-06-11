/**
 * Auth store (phase-spec §useAuthStore).
 *
 * Security policy: the access token lives in memory only; ONLY the refresh
 * token is persisted to localStorage. A reload therefore starts
 * unauthenticated and must silently refresh (api/client.ts) to recover a
 * session — hydration alone does not authenticate.
 */
import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface AuthUser {
  id: string;
  email: string;
  displayName: string | null;
}

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: AuthUser | null;
  isAuthenticated: boolean;
  /** True once the persist layer has rehydrated from localStorage. */
  hydrated: boolean;

  setSession: (access: string, refresh: string, user: AuthUser) => void;
  /** Update tokens only (after a silent refresh) without touching the user. */
  setTokens: (access: string, refresh: string) => void;
  setUser: (user: AuthUser) => void;
  clearSession: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      user: null,
      isAuthenticated: false,
      hydrated: false,

      setSession: (access, refresh, user) =>
        set({
          accessToken: access,
          refreshToken: refresh,
          user,
          isAuthenticated: true,
        }),
      // A successful silent refresh means the session is authenticated again.
      setTokens: (access, refresh) =>
        set({ accessToken: access, refreshToken: refresh, isAuthenticated: true }),
      setUser: (user) => set({ user }),
      clearSession: () =>
        set({
          accessToken: null,
          refreshToken: null,
          user: null,
          isAuthenticated: false,
        }),
    }),
    {
      name: "oriion-auth",
      // Only the refresh token is persisted — access stays in memory.
      partialize: (state) => ({ refreshToken: state.refreshToken }),
      onRehydrateStorage: () => (state) => {
        if (state) state.hydrated = true;
      },
    },
  ),
);
