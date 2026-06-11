import { describe, it, expect, vi, beforeAll } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "jest-axe";
import { Select } from "./index";

// Radix Select relies on Pointer Capture + scrollIntoView, which jsdom omits.
// Stub them so the listbox can open under the test environment.
beforeAll(() => {
  if (!Element.prototype.hasPointerCapture) {
    Element.prototype.hasPointerCapture = () => false;
  }
  if (!Element.prototype.setPointerCapture) {
    Element.prototype.setPointerCapture = () => {};
  }
  if (!Element.prototype.releasePointerCapture) {
    Element.prototype.releasePointerCapture = () => {};
  }
  if (!Element.prototype.scrollIntoView) {
    Element.prototype.scrollIntoView = () => {};
  }
});

const options = [
  { label: "Москва", value: "msk" },
  { label: "Санкт-Петербург", value: "spb" },
];

describe("Select", () => {
  it("opens via keyboard and selects an option", async () => {
    const onValueChange = vi.fn();
    render(
      <Select
        aria-label="Город"
        placeholder="Выберите город"
        options={options}
        onValueChange={onValueChange}
      />,
    );
    const trigger = screen.getByRole("combobox", { name: "Город" });
    trigger.focus();
    // Enter opens the listbox (focus lands on the first item); Enter commits it.
    await userEvent.keyboard("{Enter}");
    await screen.findByRole("listbox");
    await userEvent.keyboard("{Enter}");
    expect(onValueChange).toHaveBeenCalledWith("msk");
  });

  it("invalid sets aria-invalid on the trigger", () => {
    render(<Select aria-label="Город" options={options} invalid />);
    expect(screen.getByRole("combobox", { name: "Город" })).toHaveAttribute("aria-invalid", "true");
  });

  it("has no axe violations", async () => {
    const { container } = render(
      <Select aria-label="Город" placeholder="Город" options={options} />,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
