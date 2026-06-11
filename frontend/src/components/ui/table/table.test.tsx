import { describe, it, expect } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "jest-axe";
import type { ColumnDef } from "@tanstack/react-table";
import { Table } from "./index";

interface Row {
  name: string;
  age: number;
}

const data: Row[] = [
  { name: "Борис", age: 30 },
  { name: "Анна", age: 25 },
  { name: "Виктор", age: 42 },
];

const columns: ColumnDef<Row>[] = [
  { accessorKey: "name", header: "Имя" },
  { accessorKey: "age", header: "Возраст" },
];

describe("Table", () => {
  it("renders a row per data item", () => {
    render(<Table columns={columns} data={data} />);
    expect(screen.getByText("Борис")).toBeInTheDocument();
    expect(screen.getByText("Анна")).toBeInTheDocument();
    expect(screen.getByText("Виктор")).toBeInTheDocument();
  });

  it("renders semantic column headers", () => {
    render(<Table columns={columns} data={data} />);
    expect(screen.getByRole("columnheader", { name: "Имя" })).toBeInTheDocument();
  });

  it("toggles aria-sort when a sortable header is clicked", async () => {
    render(<Table columns={columns} data={data} sortable />);
    const header = screen.getByRole("columnheader", { name: /Имя/ });
    expect(header).toHaveAttribute("aria-sort", "none");
    await userEvent.click(within(header).getByRole("button"));
    expect(header).toHaveAttribute("aria-sort", "ascending");
    await userEvent.click(within(header).getByRole("button"));
    expect(header).toHaveAttribute("aria-sort", "descending");
  });

  it("renders the empty state when data is empty", () => {
    render(<Table columns={columns} data={[]} emptyState={<span>Ничего не найдено</span>} />);
    expect(screen.getByText("Ничего не найдено")).toBeInTheDocument();
  });

  it("sets aria-busy while loading", () => {
    const { container } = render(<Table columns={columns} data={[]} loading />);
    expect(container.querySelector("[aria-busy='true']")).toBeInTheDocument();
  });

  it("has no axe violations", async () => {
    const { container } = render(<Table columns={columns} data={data} sortable />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
