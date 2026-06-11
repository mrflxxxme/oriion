import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "jest-axe";
import { Button } from "./index";

describe("Button", () => {
  it("renders children and fires onClick", async () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Войти</Button>);
    await userEvent.click(screen.getByRole("button", { name: "Войти" }));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("loading sets aria-busy and blocks interaction", async () => {
    const onClick = vi.fn();
    render(
      <Button loading onClick={onClick}>
        Сохранить
      </Button>,
    );
    const btn = screen.getByRole("button");
    expect(btn).toHaveAttribute("aria-busy", "true");
    expect(btn).toBeDisabled();
    await userEvent.click(btn);
    expect(onClick).not.toHaveBeenCalled();
  });

  it("asChild renders the child element as the button", () => {
    render(
      <Button asChild>
        <a href="/cells">Ячейки</a>
      </Button>,
    );
    expect(screen.getByRole("link", { name: "Ячейки" })).toBeInTheDocument();
  });

  it("has no axe violations", async () => {
    const { container } = render(<Button aria-label="Закрыть" size="icon" />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
