import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "jest-axe";
import { renderWithRouter } from "@/test/helpers/renderWithProviders";
import { MemoryPanelPage } from "./MemoryPanelPage";
import { memoryApi, type MemoryEntry, type RoleMemoryEntry } from "@/api/memory";
import { agentsApi, type AgentInstance } from "@/api/agents";
import { cellsApi } from "@/api/cells";

// Spread the actual module so the page's direct imports of
// CELL_MEMORY_KINDS / ROLE_MEMORY_KINDS still resolve — only `memoryApi`
// itself is replaced with mocks.
vi.mock("@/api/memory", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/memory")>();
  return {
    ...actual,
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
  };
});
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
const listForAgent = vi.mocked(memoryApi.listForAgent);
const searchForAgent = vi.mocked(memoryApi.searchForAgent);
const addForAgent = vi.mocked(memoryApi.addForAgent);
const listForCellAgents = vi.mocked(agentsApi.listForCell);
const listWorkspaces = vi.mocked(cellsApi.listWorkspaces);
const listCells = vi.mocked(cellsApi.listCells);

function entry(overrides: Partial<MemoryEntry> = {}): MemoryEntry {
  return {
    id: "e1",
    cell_id: "c1",
    kind: "fact",
    title: "Заголовок",
    content: "Содержание записи",
    tags: [],
    source: "manual",
    contains_pii: false,
    created_at: "2026-01-01T10:00:00Z",
    updated_at: "2026-01-01T10:00:00Z",
    ...overrides,
  };
}

function roleEntry(overrides: Partial<RoleMemoryEntry> = {}): RoleMemoryEntry {
  return { ...entry(), agent_id: "ag1", ...overrides };
}

function agentInstance(overrides: Partial<AgentInstance> = {}): AgentInstance {
  return {
    id: "ag1",
    cell_id: "c1",
    agent_archetype_id: "arch1",
    custom_name: "Исследователь",
    ...overrides,
  };
}

function mount() {
  return renderWithRouter(<MemoryPanelPage />, { path: "/memory", initialEntry: "/memory" });
}

describe("MemoryPanelPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    list.mockResolvedValue([entry()]);
    search.mockResolvedValue([]);
    add.mockResolvedValue(entry({ id: "e2" }));
    removeEntry.mockResolvedValue(undefined);
    listWorkspaces.mockResolvedValue({ items: [{ id: "w1", display_name: "WS" }] });
    listCells.mockResolvedValue({
      items: [{ id: "c1", workspace_id: "w1", slug: "alpha", display_name: "Alpha" }],
    });
    listForCellAgents.mockResolvedValue([]);
    listForAgent.mockResolvedValue([]);
    searchForAgent.mockResolvedValue([]);
    addForAgent.mockResolvedValue(roleEntry({ id: "e9" }));
  });

  it("renders the heading and both tabs", async () => {
    mount();
    expect(await screen.findByRole("heading", { level: 1, name: "Память" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Ячейка" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Агент" })).toBeInTheDocument();
  });

  it("lists cell-memory entries with their source badge", async () => {
    mount();
    expect(await screen.findByText("Содержание записи")).toBeInTheDocument();
    expect(screen.getByText("Вручную")).toBeInTheDocument();
  });

  it("shows the error state with a retry action when the list query fails", async () => {
    list.mockRejectedValue(new Error("boom"));
    mount();
    expect(await screen.findByText("Не удалось загрузить память")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Повторить" })).toBeInTheDocument();
  });

  it("adds a manual cell-memory entry and refetches the list", async () => {
    const user = userEvent.setup();
    mount();
    await screen.findByText("Содержание записи");

    await user.click(screen.getByRole("button", { name: "Добавить запись" }));
    await user.type(screen.getByLabelText("Содержание"), "Новая заметка");
    await user.click(screen.getByRole("button", { name: "Запомнить" }));

    await waitFor(() => {
      expect(add).toHaveBeenCalledWith(expect.objectContaining({ content: "Новая заметка" }));
    });
  });

  it("shows a validation error when submitting an empty add form", async () => {
    const user = userEvent.setup();
    mount();
    await screen.findByText("Содержание записи");

    await user.click(screen.getByRole("button", { name: "Добавить запись" }));
    await user.click(screen.getByRole("button", { name: "Запомнить" }));

    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(add).not.toHaveBeenCalled();
  });

  it("deletes an entry after confirming in the dialog", async () => {
    const user = userEvent.setup();
    mount();
    await screen.findByText("Содержание записи");

    await user.click(screen.getByRole("button", { name: "Удалить" }));
    const dialog = await screen.findByRole("dialog");
    await user.click(within(dialog).getByRole("button", { name: "Удалить" }));

    await waitFor(() => {
      expect(removeEntry).toHaveBeenCalledWith("e1");
    });
  });

  it("cancelling the delete dialog does not call the API", async () => {
    const user = userEvent.setup();
    mount();
    await screen.findByText("Содержание записи");

    await user.click(screen.getByRole("button", { name: "Удалить" }));
    const dialog = await screen.findByRole("dialog");
    await user.click(within(dialog).getByRole("button", { name: "Отмена" }));

    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });
    expect(removeEntry).not.toHaveBeenCalled();
  });

  it("searches cell memory via the search box", async () => {
    const user = userEvent.setup();
    search.mockResolvedValue([{ entry: entry({ id: "e9", content: "Найдено" }), score: 0.87 }]);
    mount();
    await screen.findByText("Содержание записи");

    await user.type(screen.getByLabelText("Поиск по памяти"), "запрос");

    await waitFor(() => {
      expect(search).toHaveBeenCalledWith("запрос");
    });
    expect(await screen.findByText("Найдено")).toBeInTheDocument();
  });

  it("shows a placeholder on the Агент tab when the cell has no agents", async () => {
    const user = userEvent.setup();
    mount();
    await screen.findByText("Содержание записи");

    await user.click(screen.getByRole("tab", { name: "Агент" }));

    expect(await screen.findByText("Нет доступных агентов")).toBeInTheDocument();
  });

  it("loads and adds role memory for the selected agent", async () => {
    const user = userEvent.setup();
    listForCellAgents.mockResolvedValue([agentInstance()]);
    listForAgent.mockResolvedValue([roleEntry({ id: "r1", content: "Память агента" })]);
    mount();
    await screen.findByText("Содержание записи");

    await user.click(screen.getByRole("tab", { name: "Агент" }));
    expect(await screen.findByText("Память агента")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Добавить запись" }));
    await user.type(screen.getByLabelText("Содержание"), "Предпочтение агента");
    await user.click(screen.getByRole("button", { name: "Запомнить" }));

    await waitFor(() => {
      expect(addForAgent).toHaveBeenCalledWith(
        "ag1",
        expect.objectContaining({ content: "Предпочтение агента" }),
      );
    });
  });

  it("has no axe violations", async () => {
    const { container } = mount();
    await screen.findByText("Содержание записи");
    await waitFor(async () => {
      expect(await axe(container)).toHaveNoViolations();
    });
  });
});
