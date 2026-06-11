import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { axe } from "jest-axe";
import { renderWithRouter } from "@/test/helpers/renderWithProviders";
import type { Cell } from "@/api/cells";
import { useActiveCellStore } from "@/stores/active-cell";
import { CellDetailPage } from "./CellDetailPage";

const mockGetCell = vi.fn();

vi.mock("@/api/cells", () => ({
  cellsApi: {
    listAllCells: vi.fn(),
    getCell: (id: string) => mockGetCell(id) as unknown,
  },
}));

const getCell = mockGetCell;

const cell: Cell = {
  id: "c1",
  workspace_id: "w1",
  slug: "alpha-cell",
  display_name: "Альфа",
  vertical_template_slug: "marketing",
  created_at: "2024-01-15T10:00:00Z",
};

describe("CellDetailPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useActiveCellStore.setState({ activeCellId: null });
  });

  function mount() {
    return renderWithRouter(<CellDetailPage />, {
      path: "/cells/$cellId",
      initialEntry: "/cells/c1",
    });
  }

  it("renders the cell name and metadata", async () => {
    getCell.mockResolvedValue(cell);
    mount();
    expect(await screen.findByRole("heading", { level: 1, name: "Альфа" })).toBeInTheDocument();
    expect(screen.getByText("alpha-cell")).toBeInTheDocument();
    expect(screen.getByText("marketing")).toBeInTheDocument();
  });

  it("renders the «Новая задача» link to the task-create route", async () => {
    getCell.mockResolvedValue(cell);
    mount();
    const link = await screen.findByRole("link", { name: "Новая задача" });
    expect(link).toHaveAttribute("href", "/cells/c1/tasks/new");
  });

  it("sets the active cell on mount", async () => {
    getCell.mockResolvedValue(cell);
    mount();
    await screen.findByRole("heading", { level: 1, name: "Альфа" });
    expect(useActiveCellStore.getState().activeCellId).toBe("c1");
  });

  it("renders the error state when the query rejects", async () => {
    getCell.mockRejectedValue(new Error("boom"));
    mount();
    expect(
      await screen.findByRole("button", { name: "Повторить" }),
    ).toBeInTheDocument();
  });

  it("has no axe violations", async () => {
    getCell.mockResolvedValue(cell);
    const { container } = mount();
    await screen.findByRole("heading", { level: 1, name: "Альфа" });
    await waitFor(async () => {
      expect(await axe(container)).toHaveNoViolations();
    });
  });
});
