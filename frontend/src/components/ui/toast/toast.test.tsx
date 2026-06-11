import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { axe } from "jest-axe";
import { Toaster, toast } from "./index";

describe("Toaster", () => {
  it("renders without crashing", () => {
    const { container } = render(<Toaster />);
    expect(container).toBeInTheDocument();
  });

  it("has no axe violations", async () => {
    const { container } = render(<Toaster />);
    expect(await axe(container)).toHaveNoViolations();
  });
});

describe("toast helper", () => {
  it("is callable and exposes variant methods", () => {
    expect(typeof toast).toBe("function");
    expect(typeof toast.success).toBe("function");
    expect(typeof toast.error).toBe("function");
    expect(typeof toast.info).toBe("function");
    expect(typeof toast.warning).toBe("function");
    expect(typeof toast.dismiss).toBe("function");
  });
});
