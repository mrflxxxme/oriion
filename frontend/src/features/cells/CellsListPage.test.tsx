import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { axe } from "jest-axe";
import { renderWithRouter } from "@/test/helpers/renderWithProviders";
import type { Cell } from "@/api/cells";
import { CellsListPage } from "./CellsListPage";

const mockListAllCells = vi.fn();

vi.mock("@/api/cells", () => ({
  cellsApi: {
    listAllCells: () => mockListAllCells() as unknown,
    getCell: vi.fn(),
  },
}));

const listAllCells = mockListAllCells;

const cells: Cell[] = [
  {
    id: "c1",
    workspace_id: "w1",
    slug: "alpha",
    display_name: "Альфа",
    vertical_template_slug: "marketing",
    created_at: "2024-01-15T10:00:00Z",
  },
  {
    id: "c2",
    workspace_id: "w1",
    slug: "beta",
    display_name: "Бета",
    created_at: "2024-02-20T10:00:00Z",
  },
];

describe("CellsListPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  function mount() {
    return renderWithRouter(<CellsListPage />, {
      path: "/cells",
      initialEntry: "/cells",
    });
  }

  it("renders a row per cell from the API", async () => {
    listAllCells.mockResolvedValue(cells);
    mount();
    expect(await screen.findByRole("link", { name: "Альфа" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Бета" })).toBeInTheDocument();
    expect(screen.getByText("marketing")).toBeInTheDocument();
  });

  it("renders the empty state when there are no cells", async () => {
    listAllCells.mockResolvedValue([]);
    mount();
    expect(await screen.findByText("Пока нет ячеек")).toBeInTheDocument();
  });

  it("renders the error state when the query rejects", async () => {
    listAllCells.mockRejectedValue(new Error("boom"));
    mount();
    expect(
      await screen.findByRole("heading", { name: "Не удалось загрузить ячейки" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Повторить" })).toBeInTheDocument();
  });

  it("disables the create action (Wave-1 gated)", async () => {
    listAllCells.mockResolvedValue(cells);
    mount();
    await screen.findByRole("link", { name: "Альфа" });
    const create = screen.getByRole("button", { name: /Создать ячейку/ });
    expect(create).toBeDisabled();
  });

  it("has exactly one h1", async () => {
    listAllCells.mockResolvedValue(cells);
    mount();
    await screen.findByRole("link", { name: "Альфа" });
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  });

  it("has no axe violations", async () => {
    listAllCells.mockResolvedValue(cells);
    const { container } = mount();
    await screen.findByRole("link", { name: "Альфа" });
    await waitFor(async () => {
      expect(await axe(container)).toHaveNoViolations();
    });
  });
});
