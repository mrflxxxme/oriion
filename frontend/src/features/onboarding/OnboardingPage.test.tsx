import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "jest-axe";
import { renderWithRouter } from "@/test/helpers/renderWithProviders";
import { OnboardingPage } from "./OnboardingPage";
import type { Cell } from "@/api/cells";
import { teamsApi } from "@/api/teams";
import { tasksApi, type Task } from "@/api/tasks";
import { useRecentTasksStore } from "@/features/dashboard/store";

const mockListAllCells = vi.fn();
vi.mock("@/api/cells", () => ({
  cellsApi: { listAllCells: () => mockListAllCells() as unknown, getCell: vi.fn() },
}));
vi.mock("@/api/teams", () => ({ teamsApi: { provision: vi.fn() } }));
vi.mock("@/api/tasks", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/tasks")>();
  return { ...actual, tasksApi: { ...actual.tasksApi, create: vi.fn(), run: vi.fn() } };
});

const provision = vi.mocked(teamsApi.provision);
const create = vi.mocked(tasksApi.create);
const run = vi.mocked(tasksApi.run);

const cell: Cell = {
  id: "c1",
  workspace_id: "w1",
  slug: "alpha",
  display_name: "Альфа",
  created_at: "2026-01-01T10:00:00Z",
};

function makeTask(id: string): Task {
  return { id, cell_id: "c1", title: "Демо", status: "queued" };
}

function mount() {
  return renderWithRouter(<OnboardingPage />, { path: "/onboarding", initialEntry: "/onboarding" });
}

describe("OnboardingPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useRecentTasksStore.setState({ recentTasks: [] });
    mockListAllCells.mockResolvedValue([cell]);
    provision.mockResolvedValue({ team_preset_id: "p1", cell_id: "c1", agent_instances: [] });
    create.mockResolvedValue(makeTask("t1"));
    // run is blocking (~90s) in prod — never resolves during the test window.
    run.mockReturnValue(new Promise(() => undefined) as never);
  });

  it("starts on the welcome step (step 1) with a single h1", async () => {
    mount();
    expect(await screen.findByText("Добро пожаловать в Oriion")).toBeInTheDocument();
    expect(screen.getByText("Шаг 1 из 3")).toBeInTheDocument();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  });

  it("advances to the preset step and lists all three presets", async () => {
    const user = userEvent.setup();
    mount();
    await user.click(await screen.findByRole("button", { name: "Далее" }));

    expect(await screen.findByText("Выберите команду агентов")).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "Твои личные ассистенты" })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "Маркетинговое агентство" })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "Telegram-крейтор" })).toBeInTheDocument();
  });

  it("provisions the default preset (productivity-core) and advances to the task step", async () => {
    const user = userEvent.setup();
    mount();
    await user.click(await screen.findByRole("button", { name: "Далее" }));
    await user.click(await screen.findByRole("button", { name: "Продолжить" }));

    await waitFor(() => {
      expect(provision).toHaveBeenCalledWith("c1", { preset_key: "productivity-core" });
    });
    expect(await screen.findByText("Поставьте первую задачу")).toBeInTheDocument();
  });

  it("routes the telegram-creator preset through the teams API", async () => {
    const user = userEvent.setup();
    mount();
    await user.click(await screen.findByRole("button", { name: "Далее" }));
    await user.click(await screen.findByRole("radio", { name: "Telegram-крейтор" }));
    await user.click(screen.getByRole("button", { name: "Продолжить" }));

    await waitFor(() => {
      expect(provision).toHaveBeenCalledWith("c1", { preset_key: "telegram-creator" });
    });
  });

  it("submits the prefilled first task, creating and running it", async () => {
    const user = userEvent.setup();
    mount();
    await user.click(await screen.findByRole("button", { name: "Далее" }));
    await user.click(await screen.findByRole("button", { name: "Продолжить" }));

    const textarea = await screen.findByLabelText<HTMLTextAreaElement>("Описание задачи");
    expect(textarea.value.length).toBeGreaterThan(0);

    await user.click(screen.getByRole("button", { name: "Запустить задачу" }));

    await waitFor(() => {
      expect(create).toHaveBeenCalledWith(
        "c1",
        expect.objectContaining({ prompt: expect.stringContaining("бриф") }),
      );
    });
    await waitFor(() => {
      expect(run).toHaveBeenCalledWith("c1", "t1");
    });
    // The task is recorded for the dashboard's recent-tasks summary.
    expect(useRecentTasksStore.getState().recentTasks[0]?.taskId).toBe("t1");
  });

  it("shows the error state when the cell lookup fails", async () => {
    mockListAllCells.mockRejectedValue(new Error("boom"));
    mount();
    expect(await screen.findByText("Не удалось загрузить вашу ячейку")).toBeInTheDocument();
  });

  it("has no axe violations on the preset step", async () => {
    const user = userEvent.setup();
    const { container } = mount();
    await user.click(await screen.findByRole("button", { name: "Далее" }));
    await screen.findByText("Выберите команду агентов");
    await waitFor(async () => {
      expect(await axe(container)).toHaveNoViolations();
    });
  });
});
