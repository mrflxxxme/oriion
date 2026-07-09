import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { axe } from "jest-axe";
import { renderWithRouter } from "@/test/helpers/renderWithProviders";
import { DashboardPage } from "./DashboardPage";
import { billingApi, type Balance } from "@/api/billing";
import { artifactsApi, type ArtifactEnvelope } from "@/api/artifacts";
import { tasksApi, type Task } from "@/api/tasks";
import { useRecentTasksStore } from "./store";

vi.mock("@/api/billing", () => ({ billingApi: { getBalance: vi.fn() } }));
vi.mock("@/api/artifacts", () => ({ artifactsApi: { list: vi.fn() } }));
vi.mock("@/api/tasks", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/tasks")>();
  return { ...actual, tasksApi: { ...actual.tasksApi, get: vi.fn() } };
});

const getBalance = vi.mocked(billingApi.getBalance);
const listArtifacts = vi.mocked(artifactsApi.list);
const getTask = vi.mocked(tasksApi.get);

function balance(overrides: Partial<Balance> = {}): Balance {
  return {
    cell_id: "c1",
    balance_credits: "1234.5000",
    period_usage_credits: "10.0000",
    daily_usage_credits: "2.0000",
    ...overrides,
  };
}

function artifact(overrides: Partial<ArtifactEnvelope> = {}): ArtifactEnvelope {
  return {
    id: "a1",
    cell_id: "c1",
    artifact_type: "document",
    title: "Отчёт",
    tags: [],
    owner_user_id: "u1",
    created_by_agent_id: null,
    current_version_num: 1,
    created_at: "2026-01-01T10:00:00Z",
    updated_at: "2026-01-02T10:00:00Z",
    ...overrides,
  };
}

function task(overrides: Partial<Task> = {}): Task {
  return {
    id: "t1",
    cell_id: "c1",
    title: "Первая задача",
    status: "succeeded",
    created_at: "2026-01-03T09:00:00Z",
    ...overrides,
  };
}

function mount() {
  return renderWithRouter(<DashboardPage />, { path: "/dashboard", initialEntry: "/dashboard" });
}

describe("DashboardPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useRecentTasksStore.setState({ recentTasks: [] });
    getBalance.mockResolvedValue(balance());
    listArtifacts.mockResolvedValue([artifact()]);
    getTask.mockResolvedValue(task());
  });

  it("renders the heading and the credit balance from the API", async () => {
    mount();
    expect(await screen.findByRole("heading", { level: 1, name: "Дашборд" })).toBeInTheDocument();
    // 1234.50 formatted ru-RU uses a non-breaking space thousands separator.
    expect(await screen.findByText(/1\s?234,50/)).toBeInTheDocument();
  });

  it("shows the balance error state when the balance query fails", async () => {
    getBalance.mockRejectedValue(new Error("boom"));
    mount();
    expect(await screen.findByText("Не удалось загрузить баланс")).toBeInTheDocument();
  });

  it("renders the recent-tasks empty state with an onboarding CTA when none tracked", async () => {
    mount();
    expect(await screen.findByText("Пока нет задач")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Начать мастер настройки" })).toBeInTheDocument();
  });

  it("lists a tracked recent task with its live status", async () => {
    useRecentTasksStore.setState({
      recentTasks: [
        { cellId: "c1", taskId: "t1", title: "Первая задача", createdAt: "2026-01-03T09:00:00Z" },
      ],
    });
    mount();
    expect(await screen.findByRole("link", { name: "Первая задача" })).toBeInTheDocument();
    expect(await screen.findByText("Завершено")).toBeInTheDocument();
  });

  it("renders the artifacts table from the API", async () => {
    mount();
    expect(await screen.findByText("Отчёт")).toBeInTheDocument();
  });

  it("shows the artifacts empty state when there are none", async () => {
    listArtifacts.mockResolvedValue([]);
    mount();
    expect(await screen.findByText("Пока нет артефактов")).toBeInTheDocument();
  });

  it("shows the artifacts error state when the query fails", async () => {
    listArtifacts.mockRejectedValue(new Error("boom"));
    mount();
    expect(await screen.findByText("Не удалось загрузить артефакты")).toBeInTheDocument();
  });

  it("links to the memory panel", async () => {
    mount();
    expect(await screen.findByRole("link", { name: "Открыть память" })).toHaveAttribute(
      "href",
      "/memory",
    );
  });

  it("has no axe violations", async () => {
    const { container } = mount();
    await screen.findByText("Отчёт");
    await waitFor(async () => {
      expect(await axe(container)).toHaveNoViolations();
    });
  });
});
