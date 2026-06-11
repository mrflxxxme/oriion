import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "jest-axe";
import { Checkbox } from "./index";

describe("Checkbox", () => {
  it("fires onCheckedChange on click", async () => {
    const onCheckedChange = vi.fn();
    render(<Checkbox id="terms" label="Согласен" onCheckedChange={onCheckedChange} />);
    await userEvent.click(screen.getByRole("checkbox", { name: "Согласен" }));
    expect(onCheckedChange).toHaveBeenCalledWith(true);
  });

  it("clicking the label toggles the box", async () => {
    const onCheckedChange = vi.fn();
    render(<Checkbox id="news" label="Рассылка" onCheckedChange={onCheckedChange} />);
    await userEvent.click(screen.getByText("Рассылка"));
    expect(onCheckedChange).toHaveBeenCalledWith(true);
  });

  it("renders indeterminate state", () => {
    render(<Checkbox id="all" label="Все" checked="indeterminate" onCheckedChange={() => {}} />);
    expect(screen.getByRole("checkbox", { name: "Все" })).toHaveAttribute(
      "data-state",
      "indeterminate",
    );
  });

  it("has no axe violations", async () => {
    const { container } = render(<Checkbox id="ok" label="Принять" />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
