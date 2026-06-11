import { describe, it, expect, beforeEach } from "vitest";
import { useAuthStore } from "./auth";

describe("useAuthStore", () => {
  beforeEach(() => {
    localStorage.clear();
    useAuthStore.setState({
      accessToken: null,
      refreshToken: null,
      user: null,
      isAuthenticated: false,
    });
  });

  it("setSession transitions to authenticated state", () => {
    useAuthStore
      .getState()
      .setSession("access-xyz", "refresh-abc", { id: "1", email: "test@oriion.dev", displayName: "Тест" });
    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(true);
    expect(state.accessToken).toBe("access-xyz");
    expect(state.user?.email).toBe("test@oriion.dev");
  });

  it("persists ONLY the refresh token (access never written to localStorage)", () => {
    useAuthStore
      .getState()
      .setSession("access-xyz", "refresh-abc", { id: "1", email: "t@oriion.dev", displayName: null });
    const persisted = JSON.parse(localStorage.getItem("oriion-auth") ?? "{}") as {
      state?: Record<string, unknown>;
    };
    expect(persisted.state?.refreshToken).toBe("refresh-abc");
    expect(persisted.state?.accessToken).toBeUndefined();
  });

  it("setTokens rotates tokens without touching the user", () => {
    useAuthStore
      .getState()
      .setSession("a1", "r1", { id: "1", email: "t@oriion.dev", displayName: null });
    useAuthStore.getState().setTokens("a2", "r2");
    const state = useAuthStore.getState();
    expect(state.accessToken).toBe("a2");
    expect(state.refreshToken).toBe("r2");
    expect(state.user?.id).toBe("1");
  });

  it("clearSession resets to unauthenticated", () => {
    useAuthStore.getState().setSession("a", "r", { id: "1", email: "t@oriion.dev", displayName: null });
    useAuthStore.getState().clearSession();
    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(false);
    expect(state.accessToken).toBeNull();
    expect(state.user).toBeNull();
  });
});
