import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "jest-axe";
import { RadioGroup } from "./index";

const options = [
  { label: "Дневная", value: "day" },
  { label: "Ночная", value: "night" },
];

describe("RadioGroup", () => {
  it("renders a radiogroup with options", () => {
    render(<RadioGroup aria-label="Смена" options={options} />);
    expect(screen.getByRole("radiogroup")).toBeInTheDocument();
    expect(screen.getAllByRole("radio")).toHaveLength(2);
  });

  it("fires onValueChange on selection", async () => {
    const onValueChange = vi.fn();
    render(<RadioGroup aria-label="Смена" options={options} onValueChange={onValueChange} />);
    await userEvent.click(screen.getByRole("radio", { name: "Ночная" }));
    expect(onValueChange).toHaveBeenCalledWith("night");
  });

  it("has no axe violations", async () => {
    const { container } = render(<RadioGroup aria-label="Смена" options={options} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
