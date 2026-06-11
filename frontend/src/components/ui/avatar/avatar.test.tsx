import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { axe } from "jest-axe";
import { Avatar } from "./index";

describe("Avatar", () => {
  it("renders fallback initials", () => {
    render(<Avatar fallback="КУ" />);
    expect(screen.getByText("КУ")).toBeInTheDocument();
  });

  it("exposes status via aria-label", () => {
    render(<Avatar fallback="АБ" status="online" />);
    expect(screen.getByRole("status")).toHaveAttribute("aria-label", "В сети");
  });

  it("maps each status to its Russian label", () => {
    const { rerender } = render(<Avatar fallback="X" status="busy" />);
    expect(screen.getByRole("status")).toHaveAttribute("aria-label", "Занят");
    rerender(<Avatar fallback="X" status="away" />);
    expect(screen.getByRole("status")).toHaveAttribute("aria-label", "Отошёл");
    rerender(<Avatar fallback="X" status="offline" />);
    expect(screen.getByRole("status")).toHaveAttribute("aria-label", "Не в сети");
  });

  it("has no axe violations", async () => {
    const { container } = render(<Avatar fallback="КУ" status="online" />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
