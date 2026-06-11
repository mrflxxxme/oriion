import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "jest-axe";
import { TaskProgressStream } from "./TaskProgressStream";
import { replayProgress } from "./progress-reducer";
import { parseSseTranscript } from "@/api/sse";
import transcript from "../../test/fixtures/sse-market-brief.transcript.txt?raw";

const completed = replayProgress(parseSseTranscript(transcript));

describe("TaskProgressStream", () => {
  it("renders the three agent cards with their Russian labels", () => {
    render(<TaskProgressStream progress={completed} isRunning={false} streamError={false} />);
    expect(screen.getByText("Исследователь")).toBeInTheDocument();
    expect(screen.getByText("Аналитик")).toBeInTheDocument();
    expect(screen.getByText("Райтер")).toBeInTheDocument();
    // all done after replay
    expect(screen.getAllByText("Готово")).toHaveLength(3);
  });

  it("sets aria-busy while running", () => {
    const { container } = render(
      <TaskProgressStream progress={completed} isRunning streamError={false} />,
    );
    expect(container.querySelector('[aria-busy="true"]')).not.toBeNull();
  });

  it("toggles the raw event log", async () => {
    render(<TaskProgressStream progress={completed} isRunning={false} streamError={false} />);
    const toggle = screen.getByRole("button", { name: /журнал событий/i });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    await userEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText("task.completed")).toBeInTheDocument();
  });

  it("shows the stream-error fallback notice", () => {
    render(<TaskProgressStream progress={completed} isRunning={false} streamError />);
    expect(screen.getByRole("status")).toHaveTextContent(/опросом/i);
  });

  it("has no axe violations", async () => {
    const { container } = render(
      <TaskProgressStream progress={completed} isRunning={false} streamError={false} />,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
