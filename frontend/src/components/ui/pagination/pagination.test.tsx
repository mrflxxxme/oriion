import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "jest-axe";
import { Pagination } from "./index";

describe("Pagination", () => {
  it("renders nothing when totalPages <= 1", () => {
    const { container } = render(
      <Pagination currentPage={1} totalPages={1} onPageChange={vi.fn()} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("fires onPageChange with the clicked page", async () => {
    const onPageChange = vi.fn();
    render(<Pagination currentPage={1} totalPages={5} onPageChange={onPageChange} />);
    await userEvent.click(screen.getByRole("button", { name: "Страница 3" }));
    expect(onPageChange).toHaveBeenCalledWith(3);
  });

  it("marks the current page with aria-current", () => {
    render(<Pagination currentPage={2} totalPages={5} onPageChange={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Страница 2" })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });

  it("disables prev/first on page 1", () => {
    render(<Pagination currentPage={1} totalPages={5} onPageChange={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Предыдущая страница" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Первая страница" })).toBeDisabled();
  });

  it("disables next/last on the final page", () => {
    render(<Pagination currentPage={5} totalPages={5} onPageChange={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Следующая страница" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Последняя страница" })).toBeDisabled();
  });

  it("hides first/last controls when showFirstLast is false", () => {
    render(
      <Pagination currentPage={1} totalPages={5} showFirstLast={false} onPageChange={vi.fn()} />,
    );
    expect(screen.queryByRole("button", { name: "Первая страница" })).not.toBeInTheDocument();
  });

  it("has no axe violations", async () => {
    const { container } = render(
      <Pagination currentPage={3} totalPages={10} onPageChange={vi.fn()} />,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
