import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { axe } from "jest-axe";
import { Breadcrumb } from "./index";

const items = [
  { label: "Главная", href: "/" },
  { label: "Ячейки", href: "/cells" },
  { label: "Ячейка 42" },
];

describe("Breadcrumb", () => {
  it("renders a labelled nav", () => {
    render(<Breadcrumb items={items} />);
    expect(screen.getByRole("navigation", { name: "Breadcrumb" })).toBeInTheDocument();
  });

  it("marks the last item as current page", () => {
    render(<Breadcrumb items={items} />);
    const current = screen.getByText("Ячейка 42");
    expect(current).toHaveAttribute("aria-current", "page");
  });

  it("renders intermediate items as links", () => {
    render(<Breadcrumb items={items} />);
    expect(screen.getByRole("link", { name: "Ячейки" })).toHaveAttribute("href", "/cells");
  });

  it("collapses the middle past maxItems", () => {
    const many = [
      { label: "A", href: "/a" },
      { label: "B", href: "/b" },
      { label: "C", href: "/c" },
      { label: "D", href: "/d" },
      { label: "E" },
    ];
    render(<Breadcrumb items={many} maxItems={3} />);
    expect(screen.getByText("…")).toBeInTheDocument();
    expect(screen.queryByText("B")).not.toBeInTheDocument();
    expect(screen.getByText("A")).toBeInTheDocument();
    expect(screen.getByText("E")).toHaveAttribute("aria-current", "page");
  });

  it("has no axe violations", async () => {
    const { container } = render(<Breadcrumb items={items} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
