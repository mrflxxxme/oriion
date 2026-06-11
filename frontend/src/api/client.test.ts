import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { z } from "zod";
import { apiFetch, ApiException } from "./client";
import { useAuthStore } from "@/stores/auth";

function jsonResponse(status: number, body: unknown): Response {
  return new Response(body === undefined ? null : JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("apiFetch", () => {
  beforeEach(() => {
    useAuthStore.setState({
      accessToken: "access-1",
      refreshToken: "refresh-1",
      user: null,
      isAuthenticated: true,
    });
  });
  afterEach(() => vi.restoreAllMocks());

  it("injects the Bearer token and validates against a schema", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, { id: "c1", name: "Cell" }));
    vi.stubGlobal("fetch", fetchMock);

    const schema = z.object({ id: z.string(), name: z.string() });
    const data = await apiFetch("/cells/c1", { schema });

    expect(data).toEqual({ id: "c1", name: "Cell" });
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect((init.headers as Record<string, string>)["Authorization"]).toBe("Bearer access-1");
  });

  it("maps backend error codes to Russian copy via ApiException", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse(401, { code: "iam.auth.invalid_credentials" })),
    );
    await expect(apiFetch("/users/me", { authRequired: false })).rejects.toMatchObject({
      error: { code: "iam.auth.invalid_credentials", message: "Неверный email или пароль." },
    });
  });

  it("on 401: refreshes once then retries the original request", async () => {
    const fetchMock = vi
      .fn()
      // 1) original request → 401
      .mockResolvedValueOnce(jsonResponse(401, { code: "iam.token.invalid" }))
      // 2) refresh → new pair
      .mockResolvedValueOnce(
        jsonResponse(200, { access_token: "access-2", refresh_token: "refresh-2" }),
      )
      // 3) retry → success
      .mockResolvedValueOnce(jsonResponse(200, { ok: true }));
    vi.stubGlobal("fetch", fetchMock);

    const data = await apiFetch<{ ok: boolean }>("/users/me");
    expect(data).toEqual({ ok: true });
    expect(useAuthStore.getState().accessToken).toBe("access-2");

    // The retry carried the refreshed token.
    const [, retryInit] = fetchMock.mock.calls[2] as [string, RequestInit];
    expect((retryInit.headers as Record<string, string>)["Authorization"]).toBe("Bearer access-2");
  });

  it("on 401 with a failing refresh: clears the session and throws", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(401, { code: "iam.token.invalid" }))
      .mockResolvedValueOnce(jsonResponse(401, {})); // refresh fails
    vi.stubGlobal("fetch", fetchMock);

    await expect(apiFetch("/users/me")).rejects.toBeInstanceOf(ApiException);
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
  });
});
