import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { artifactsApi } from "./artifacts";
import { useAuthStore } from "@/stores/auth";

function jsonResponse(status: number, body: unknown): Response {
  return new Response(body === undefined ? null : JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function artifact(id: string): unknown {
  return {
    id,
    cell_id: "c1",
    artifact_type: "document",
    title: "Отчёт",
    tags: [],
    owner_user_id: "u1",
    created_by_agent_id: null,
    current_version_num: 1,
    created_at: "2026-01-01T10:00:00Z",
    updated_at: "2026-01-02T10:00:00Z",
  };
}

describe("artifactsApi", () => {
  beforeEach(() => {
    useAuthStore.setState({
      accessToken: "access-1",
      refreshToken: "refresh-1",
      user: null,
      isAuthenticated: true,
    });
  });
  afterEach(() => vi.restoreAllMocks());

  it("list() GETs /artifacts with the limit query param", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, [artifact("a1")]));
    vi.stubGlobal("fetch", fetchMock);

    const result = await artifactsApi.list({ limit: 5 });

    expect(result).toHaveLength(1);
    const [url] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/v1/artifacts?limit=5");
  });

  it("list() omits the query string when no params are given", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, []));
    vi.stubGlobal("fetch", fetchMock);

    await artifactsApi.list();

    const [url] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/v1/artifacts");
  });
});
