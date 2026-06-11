import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { axe } from "jest-axe";
import { Badge } from "./index";

describe("Badge", () => {
  it("renders children", () => {
    render(<Badge>Активна</Badge>);
    expect(screen.getByText("Активна")).toBeInTheDocument();
  });

  it("applies variant class", () => {
    render(<Badge variant="success">Готово</Badge>);
    const el = screen.getByText("Готово");
    expect(el.className).toContain("bg-success-100");
    expect(el.className).toContain("text-success-700");
  });

  it("applies size class", () => {
    render(<Badge size="md">Большой</Badge>);
    expect(screen.getByText("Большой").className).toContain("text-sm");
  });

  it("has no axe violations", async () => {
    const { container } = render(<Badge variant="danger">Ошибка</Badge>);
    expect(await axe(container)).toHaveNoViolations();
  });
});
