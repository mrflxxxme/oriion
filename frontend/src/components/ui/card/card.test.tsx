import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "jest-axe";
import { Card } from "./index";

describe("Card", () => {
  it("renders compound slots", () => {
    render(
      <Card>
        <Card.Header>Заголовок</Card.Header>
        <Card.Body>Тело</Card.Body>
        <Card.Footer>Подвал</Card.Footer>
      </Card>,
    );
    expect(screen.getByText("Заголовок")).toBeInTheDocument();
    expect(screen.getByText("Тело")).toBeInTheDocument();
    expect(screen.getByText("Подвал")).toBeInTheDocument();
  });

  it("interactive card is a focusable button and fires onClick", async () => {
    const onClick = vi.fn();
    render(
      <Card interactive onClick={onClick}>
        <Card.Body>Кликни</Card.Body>
      </Card>,
    );
    const card = screen.getByRole("button");
    expect(card).toHaveAttribute("tabindex", "0");
    await userEvent.click(card);
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("elevated variant adds shadow", () => {
    const { container } = render(<Card variant="elevated">x</Card>);
    expect(container.firstElementChild).toHaveClass("shadow-md");
  });

  it("has no axe violations", async () => {
    const { container } = render(
      <Card>
        <Card.Header>Карточка</Card.Header>
        <Card.Body>Содержимое</Card.Body>
      </Card>,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
