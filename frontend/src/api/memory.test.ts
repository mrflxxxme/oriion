import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { memoryApi, type MemoryEntry } from "./memory";
import { useAuthStore } from "@/stores/auth";

function jsonResponse(status: number, body: unknown): Response {
  return new Response(body === undefined ? null : JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function entry(overrides: Partial<MemoryEntry & { agent_id: string }> = {}) {
  return {
    id: "e1",
    cell_id: "c1",
    kind: "fact",
    title: null,
    content: "hello",
    tags: [],
    source: "manual",
    contains_pii: false,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

describe("memoryApi", () => {
  beforeEach(() => {
    useAuthStore.setState({
      accessToken: "access-1",
      refreshToken: "refresh-1",
      user: null,
      isAuthenticated: true,
    });
  });
  afterEach(() => vi.restoreAllMocks());

  it("list() GETs /memory with limit/offset query params", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, [entry()]));
    vi.stubGlobal("fetch", fetchMock);

    const data = await memoryApi.list({ limit: 10, offset: 5 });

    expect(data).toHaveLength(1);
    const [url] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/v1/memory?limit=10&offset=5");
  });

  it("list() omits the query string when no options are given", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, []));
    vi.stubGlobal("fetch", fetchMock);

    await memoryApi.list();

    const [url] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/v1/memory");
  });

  it("search() uses the backend's `q` query param (not `query`)", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(jsonResponse(200, [{ entry: entry(), score: 0.91 }]));
    vi.stubGlobal("fetch", fetchMock);

    const hits = await memoryApi.search("foo", 5);

    expect(hits[0]?.score).toBe(0.91);
    const [url] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/v1/memory/search?q=foo&limit=5");
  });

  it("add() POSTs to /memory and returns the created entry", async () => {
    const created = entry({ id: "e2" });
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(201, created));
    vi.stubGlobal("fetch", fetchMock);

    const result = await memoryApi.add({ content: "x", kind: "fact" });

    expect(result.id).toBe("e2");
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/v1/memory");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body as string)).toEqual({ content: "x", kind: "fact" });
  });

  it("remove() DELETEs /memory/{id} and resolves undefined on 204", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(204, undefined));
    vi.stubGlobal("fetch", fetchMock);

    const result = await memoryApi.remove("e1");

    expect(result).toBeUndefined();
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/v1/memory/e1");
    expect(init.method).toBe("DELETE");
  });

  it("role-memory endpoints hit /memory/agents/{agentId}[...]", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(200, [entry({ agent_id: "a1" })]))
      .mockResolvedValueOnce(jsonResponse(200, [{ entry: entry({ agent_id: "a1" }), score: 0.5 }]))
      .mockResolvedValueOnce(jsonResponse(201, entry({ id: "e3", agent_id: "a1" })))
      .mockResolvedValueOnce(jsonResponse(204, undefined));
    vi.stubGlobal("fetch", fetchMock);

    await memoryApi.listForAgent("a1");
    await memoryApi.searchForAgent("a1", "bar");
    await memoryApi.addForAgent("a1", { content: "y" });
    await memoryApi.removeForAgent("a1", "e3");

    const urls = fetchMock.mock.calls.map((call) => call[0] as string);
    expect(urls).toEqual([
      "/api/v1/memory/agents/a1",
      "/api/v1/memory/agents/a1/search?q=bar",
      "/api/v1/memory/agents/a1",
      "/api/v1/memory/agents/a1/e3",
    ]);
  });
});
