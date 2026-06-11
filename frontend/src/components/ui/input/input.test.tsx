import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "jest-axe";
import { Input } from "./index";

describe("Input", () => {
  it("accepts typed text", async () => {
    render(
      <>
        <label htmlFor="email">Эл. почта</label>
        <Input id="email" />
      </>,
    );
    const input = screen.getByLabelText("Эл. почта");
    await userEvent.type(input, "test@oriion.ru");
    expect(input).toHaveValue("test@oriion.ru");
  });

  it("invalid sets aria-invalid", () => {
    render(
      <>
        <label htmlFor="name">Имя</label>
        <Input id="name" invalid />
      </>,
    );
    expect(screen.getByLabelText("Имя")).toHaveAttribute("aria-invalid", "true");
  });

  it("renders prefix and suffix adornments", () => {
    render(
      <>
        <label htmlFor="amount">Сумма</label>
        <Input id="amount" prefix="₽" suffix=".00" />
      </>,
    );
    expect(screen.getByText("₽")).toBeInTheDocument();
    expect(screen.getByText(".00")).toBeInTheDocument();
  });

  it("has no axe violations", async () => {
    const { container } = render(
      <>
        <label htmlFor="login">Логин</label>
        <Input id="login" />
      </>,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
