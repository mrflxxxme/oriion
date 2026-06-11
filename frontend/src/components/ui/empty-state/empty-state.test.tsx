import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "jest-axe";
import { EmptyState } from "./index";

describe("EmptyState", () => {
  it("renders the title and description", () => {
    render(<EmptyState title="Нет ячеек" description="Создайте первую ячейку, чтобы начать." />);
    expect(screen.getByRole("heading", { name: "Нет ячеек" })).toBeInTheDocument();
    expect(screen.getByText("Создайте первую ячейку, чтобы начать.")).toBeInTheDocument();
  });

  it("fires the action onClick", async () => {
    const onClick = vi.fn();
    render(<EmptyState title="Нет ячеек" action={{ label: "Создать", onClick }} />);
    await userEvent.click(screen.getByRole("button", { name: "Создать" }));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("marks the illustration as decorative", () => {
    const { container } = render(
      <EmptyState title="Нет данных" illustration={<svg data-testid="art" />} />,
    );
    const decorative = container.querySelector('[aria-hidden="true"]');
    expect(decorative).not.toBeNull();
    expect(screen.getByTestId("art")).toBeInTheDocument();
  });

  it("danger variant renders a default icon and danger heading", () => {
    render(<EmptyState variant="danger" title="Ошибка загрузки" />);
    const heading = screen.getByRole("heading", { name: "Ошибка загрузки" });
    expect(heading.className).toContain("text-danger-600");
  });

  it("has no axe violations", async () => {
    const { container } = render(
      <EmptyState
        title="Нет ячеек"
        description="Создайте первую ячейку."
        action={{ label: "Создать", onClick: vi.fn() }}
      />,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
