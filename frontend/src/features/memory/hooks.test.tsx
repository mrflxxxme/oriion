import { describe, it, expect, vi, beforeEach } from "vitest";
import type { ReactNode } from "react";
import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClientProvider } from "@tanstack/react-query";
import { createTestQueryClient } from "@/test/helpers/createTestQueryClient";
import { memoryApi, type MemoryEntry } from "@/api/memory";
import { agentsApi } from "@/api/agents";
import { cellsApi } from "@/api/cells";
import {
  useAddCellMemory,
  useCellAgents,
  useCellMemoryList,
  useCellMemorySearch,
  useCurrentCellId,
  useDeleteCellMemory,
} from "./hooks";

vi.mock("@/api/memory", () => ({
  memoryApi: {
    list: vi.fn(),
    search: vi.fn(),
    add: vi.fn(),
    remove: vi.fn(),
    listForAgent: vi.fn(),
    searchForAgent: vi.fn(),
    addForAgent: vi.fn(),
    removeForAgent: vi.fn(),
  },
}));
vi.mock("@/api/agents", () => ({ agentsApi: { listForCell: vi.fn() } }));
// `cellsApi.listAllCells` is a `this`-using method (fans out over
// listWorkspaces/listCells) — mock its two leaf calls instead of the method
// itself so `vi.mocked(cellsApi.listAllCells)` doesn't trip
// @typescript-eslint/unbound-method.
vi.mock("@/api/cells", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/cells")>();
  return {
    ...actual,
    cellsApi: { ...actual.cellsApi, listWorkspaces: vi.fn(), listCells: vi.fn() },
  };
});

const list = vi.mocked(memoryApi.list);
const search = vi.mocked(memoryApi.search);
const add = vi.mocked(memoryApi.add);
const removeEntry = vi.mocked(memoryApi.remove);
const listForCellAgents = vi.mocked(agentsApi.listForCell);
const listWorkspaces = vi.mocked(cellsApi.listWorkspaces);
const listCells = vi.mocked(cellsApi.listCells);

function entry(overrides: Partial<MemoryEntry> = {}): MemoryEntry {
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

function makeWrapper() {
  const queryClient = createTestQueryClient();
  function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  }
  return Wrapper;
}

describe("useCellMemorySearch", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("does not call the API when the query is blank", () => {
    renderHook(() => useCellMemorySearch("   "), { wrapper: makeWrapper() });
    expect(search).not.toHaveBeenCalled();
  });

  it("calls the API with the trimmed query when non-blank", async () => {
    search.mockResolvedValue([]);
    renderHook(() => useCellMemorySearch("  hello  "), { wrapper: makeWrapper() });
    await waitFor(() => {
      expect(search).toHaveBeenCalledWith("hello");
    });
  });
});

describe("cell-memory mutations", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("useAddCellMemory invalidates the cell-memory list on success", async () => {
    list.mockResolvedValue([]);
    add.mockResolvedValue(entry({ id: "e2" }));
    const wrapper = makeWrapper();

    const { result: listResult } = renderHook(() => useCellMemoryList(), { wrapper });
    await waitFor(() => {
      expect(listResult.current.isSuccess).toBe(true);
    });
    expect(list).toHaveBeenCalledTimes(1);

    const { result: addResult } = renderHook(() => useAddCellMemory(), { wrapper });
    act(() => {
      addResult.current.mutate({ content: "new" });
    });

    await waitFor(() => {
      expect(list).toHaveBeenCalledTimes(2);
    });
  });

  it("useDeleteCellMemory invalidates the cell-memory list on success", async () => {
    list.mockResolvedValue([entry()]);
    removeEntry.mockResolvedValue(undefined);
    const wrapper = makeWrapper();

    const { result: listResult } = renderHook(() => useCellMemoryList(), { wrapper });
    await waitFor(() => {
      expect(listResult.current.isSuccess).toBe(true);
    });
    expect(list).toHaveBeenCalledTimes(1);

    const { result: deleteResult } = renderHook(() => useDeleteCellMemory(), { wrapper });
    act(() => {
      deleteResult.current.mutate("e1");
    });

    await waitFor(() => {
      expect(removeEntry).toHaveBeenCalledWith("e1");
      expect(list).toHaveBeenCalledTimes(2);
    });
  });
});

describe("useCellAgents / useCurrentCellId", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("useCellAgents stays disabled until a cellId is available", () => {
    renderHook(() => useCellAgents(undefined), { wrapper: makeWrapper() });
    expect(listForCellAgents).not.toHaveBeenCalled();
  });

  it("useCellAgents queries once a cellId resolves", async () => {
    listForCellAgents.mockResolvedValue([]);
    renderHook(() => useCellAgents("c1"), { wrapper: makeWrapper() });
    await waitFor(() => {
      expect(listForCellAgents).toHaveBeenCalledWith("c1");
    });
  });

  it("useCurrentCellId resolves the first cell across the user's workspaces", async () => {
    listWorkspaces.mockResolvedValue({ items: [{ id: "w1", display_name: "WS" }] });
    listCells.mockResolvedValue({
      items: [{ id: "c1", workspace_id: "w1", slug: "alpha", display_name: "Alpha" }],
    });
    const { result } = renderHook(() => useCurrentCellId(), { wrapper: makeWrapper() });
    await waitFor(() => {
      expect(result.current).toBe("c1");
    });
  });
});
