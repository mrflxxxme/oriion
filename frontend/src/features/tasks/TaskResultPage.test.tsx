import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "jest-axe";
import { renderWithRouter } from "@/test/helpers/renderWithProviders";
import { parseSseTranscript } from "@/api/sse";
import transcript from "../../test/fixtures/sse-market-brief.transcript.txt?raw";
import { TaskResultPage } from "./TaskResultPage";

const fixtureEvents = parseSseTranscript(transcript);

vi.mock("@/api/tasks", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/tasks")>();
  return {
    ...actual,
    tasksApi: {
      get: vi.fn().mockResolvedValue({
        id: "t1",
        cell_id: "c1",
        title: "Market & content brief",
        status: "succeeded",
        total_cost_credits: "1.42",
        total_input_tokens: 100,
        total_output_tokens: 200,
      }),
      cancel: vi.fn().mockResolvedValue({}),
    },
  };
});

// Drive the SSE hook by replaying the live fixture synchronously.
vi.mock("@/api/sse", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/sse")>();
  return {
    ...actual,
    streamSse: vi.fn(
      (_url: string, _token: string | null, opts: { onEvent: (e: unknown) => void }) => {
        for (const event of fixtureEvents) opts.onEvent(event);
        return Promise.resolve();
      },
    ),
  };
});

function mountResult() {
  return renderWithRouter(<TaskResultPage />, {
    path: "/cells/$cellId/tasks/$taskId",
    initialEntry: "/cells/c1/tasks/t1",
  });
}

describe("TaskResultPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the three tabs and the agent progress cards", async () => {
    mountResult();
    await waitFor(() => {
      expect(screen.getByRole("tab", { name: /прогресс/i })).toBeInTheDocument();
    });
    expect(screen.getByRole("tab", { name: /результат/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /стоимость/i })).toBeInTheDocument();
    expect(screen.getByText("Исследователь")).toBeInTheDocument();
  });

  it("renders the 3 markdown artifacts on the Результат tab", async () => {
    mountResult();
    await waitFor(() => {
      expect(screen.getByRole("tab", { name: /результат/i })).toBeInTheDocument();
    });
    await userEvent.click(screen.getByRole("tab", { name: /результат/i }));
    await waitFor(() => {
      expect(screen.getByRole("region", { name: /итоговый ответ/i })).toBeInTheDocument();
    });
    expect(screen.getByRole("heading", { name: /матрица исследования/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /бриф и контент-план/i })).toBeInTheDocument();
  });

  it("has no axe violations", async () => {
    const { container } = mountResult();
    await waitFor(() => {
      expect(screen.getByText("Исследователь")).toBeInTheDocument();
    });
    expect(await axe(container)).toHaveNoViolations();
  });
});
