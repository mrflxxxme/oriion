import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { teamsApi } from "./teams";
import { useAuthStore } from "@/stores/auth";

function jsonResponse(status: number, body: unknown): Response {
  return new Response(body === undefined ? null : JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("teamsApi", () => {
  beforeEach(() => {
    useAuthStore.setState({
      accessToken: "access-1",
      refreshToken: "refresh-1",
      user: null,
      isAuthenticated: true,
    });
  });
  afterEach(() => vi.restoreAllMocks());

  it("provision() POSTs /cells/{cellId}/teams with the preset_key", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse(201, {
        team_preset_id: "p1",
        cell_id: "c1",
        agent_instances: [
          { id: "ai1", cell_id: "c1", agent_archetype_id: "arch1", custom_name: null },
        ],
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await teamsApi.provision("c1", { preset_key: "telegram-creator" });

    expect(result.team_preset_id).toBe("p1");
    expect(result.agent_instances).toHaveLength(1);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/v1/cells/c1/teams");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body as string)).toEqual({ preset_key: "telegram-creator" });
  });
});
