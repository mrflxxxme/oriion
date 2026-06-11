import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { axe } from "jest-axe";
import { Skeleton } from "./index";

describe("Skeleton", () => {
  it("renders N bars for the text variant", () => {
    const { container } = render(<Skeleton variant="text" lines={3} />);
    const bars = container.querySelectorAll('[aria-hidden="true"]');
    expect(bars).toHaveLength(3);
  });

  it("marks bars as decorative (aria-hidden)", () => {
    const { container } = render(<Skeleton />);
    const bar = container.querySelector('[aria-hidden="true"]');
    expect(bar).not.toBeNull();
  });

  it("applies dynamic width/height via inline style", () => {
    const { container } = render(<Skeleton width={120} height="2rem" />);
    const bar = container.querySelector('[aria-hidden="true"]') as HTMLElement;
    expect(bar.style.width).toBe("120px");
    expect(bar.style.height).toBe("2rem");
  });

  it("uses the pulse animation", () => {
    const { container } = render(<Skeleton />);
    const bar = container.querySelector('[aria-hidden="true"]') as HTMLElement;
    expect(bar.className).toContain("animate-pulse");
  });

  it("has no axe violations", async () => {
    const { container } = render(
      <div role="status" aria-busy="true" aria-label="Загрузка">
        <Skeleton variant="text" lines={2} />
      </div>,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
