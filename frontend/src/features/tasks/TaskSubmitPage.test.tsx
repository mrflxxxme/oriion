import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "jest-axe";
import { renderWithRouter } from "@/test/helpers/renderWithProviders";
import { TaskSubmitPage } from "./TaskSubmitPage";
import { tasksApi, type Task } from "@/api/tasks";

vi.mock("@/api/tasks", () => ({
  tasksApi: {
    create: vi.fn(),
    run: vi.fn(),
  },
}));

const mockCreate = vi.mocked(tasksApi.create);
const mockRun = vi.mocked(tasksApi.run);

function makeTask(id: string, prompt: string): Task {
  return {
    id,
    cell_id: "c1",
    title: prompt.slice(0, 20),
    status: "queued",
  };
}

function mount() {
  return renderWithRouter(<TaskSubmitPage />, {
    path: "/cells/$cellId/tasks/new",
    initialEntry: "/cells/c1/tasks/new",
  });
}

describe("TaskSubmitPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockCreate.mockResolvedValue(makeTask("t1", "x"));
    // run is blocking (~90s) in prod — never resolves during the test window.
    mockRun.mockReturnValue(new Promise(() => undefined) as never);
  });

  it("renders exactly one h1", async () => {
    mount();
    await screen.findByRole("heading", { level: 1 });
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  });

  it("preset chip fills the textarea with the proven prompt", async () => {
    const user = userEvent.setup();
    mount();
    await user.click(await screen.findByRole("button", { name: "Маркет-бриф" }));
    const textarea = screen.getByLabelText("Опишите задачу");
    expect((textarea as HTMLTextAreaElement).value).toContain("market brief");
  });

  it("shows a validation error when submitting empty", async () => {
    const user = userEvent.setup();
    mount();
    await user.click(await screen.findByRole("button", { name: "Создать задачу" }));
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(mockCreate).not.toHaveBeenCalled();
  });

  it("submitting a valid prompt calls create then fires run (without awaiting)", async () => {
    const user = userEvent.setup();
    mount();
    const textarea = await screen.findByLabelText("Опишите задачу");
    await user.type(textarea, "Сделай market brief");
    await user.click(screen.getByRole("button", { name: "Создать задачу" }));

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith("c1", {
        title: expect.any(String),
        prompt: "Сделай market brief",
      });
    });
    await waitFor(() => {
      expect(mockRun).toHaveBeenCalledWith("c1", "t1");
    });
  });

  it("has no axe violations", async () => {
    const { container } = mount();
    await screen.findByRole("heading", { level: 1 });
    expect(await axe(container)).toHaveNoViolations();
  });
});
