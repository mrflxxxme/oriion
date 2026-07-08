import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { agentsApi } from "./agents";
import { useAuthStore } from "@/stores/auth";

function jsonResponse(status: number, body: unknown): Response {
  return new Response(body === undefined ? null : JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("agentsApi", () => {
  beforeEach(() => {
    useAuthStore.setState({
      accessToken: "access-1",
      refreshToken: "refresh-1",
      user: null,
      isAuthenticated: true,
    });
  });
  afterEach(() => vi.restoreAllMocks());

  it("listForCell() GETs /cells/{cellId}/agents", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(
        jsonResponse(200, [
          { id: "ai1", cell_id: "c1", agent_archetype_id: "arch1", custom_name: "Researcher" },
        ]),
      );
    vi.stubGlobal("fetch", fetchMock);

    const result = await agentsApi.listForCell("c1");

    expect(result).toEqual([
      { id: "ai1", cell_id: "c1", agent_archetype_id: "arch1", custom_name: "Researcher" },
    ]);
    const [url] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/v1/cells/c1/agents");
  });
});
