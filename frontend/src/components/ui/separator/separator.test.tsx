import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { axe } from "jest-axe";
import { Separator } from "./index";

describe("Separator", () => {
  it("renders a decorative divider by default (no separator role)", () => {
    const { container } = render(<Separator />);
    const el = container.firstElementChild;
    expect(el).toHaveClass("h-px", "w-full");
    // decorative → aria-hidden, no implicit separator role.
    expect(el).toHaveAttribute("data-orientation", "horizontal");
  });

  it("exposes a separator role when not decorative", () => {
    const { getByRole } = render(<Separator decorative={false} orientation="vertical" />);
    const sep = getByRole("separator");
    expect(sep).toHaveClass("h-full", "w-px");
    expect(sep).toHaveAttribute("aria-orientation", "vertical");
  });

  it("has no axe violations", async () => {
    const { container } = render(<Separator decorative={false} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
