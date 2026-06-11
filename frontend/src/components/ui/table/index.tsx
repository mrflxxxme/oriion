/**
 * Table — generic data grid (component-inventory.md #13).
 * Wraps @tanstack/react-table for headless sorting; renders a semantic <table>.
 * Pagination is intentionally NOT handled here (see ui/pagination).
 */
import { useState } from "react";
import type { ReactNode } from "react";
import {
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type ColumnDef,
  type SortingState,
} from "@tanstack/react-table";
import { ChevronDown, ChevronUp } from "lucide-react";
import { cn } from "@/lib/utils";

export interface TableProps<TData> {
  columns: ColumnDef<TData, unknown>[];
  data: TData[];
  sortable?: boolean;
  loading?: boolean;
  emptyState?: ReactNode;
  density?: "comfortable" | "compact";
}

const cellPadding: Record<NonNullable<TableProps<unknown>["density"]>, string> = {
  comfortable: "px-4 py-3",
  compact: "px-3 py-1.5",
};

const SKELETON_ROWS = 4;

export function Table<TData>({
  columns,
  data,
  sortable = false,
  loading = false,
  emptyState,
  density = "comfortable",
}: TableProps<TData>) {
  const [sorting, setSorting] = useState<SortingState>([]);

  const table = useReactTable<TData>({
    data,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    ...(sortable ? { getSortedRowModel: getSortedRowModel() } : {}),
    enableSorting: sortable,
  });

  const pad = cellPadding[density];
  const headerGroups = table.getHeaderGroups();
  const rows = table.getRowModel().rows;
  const isEmpty = !loading && data.length === 0;

  return (
    <div className="w-full overflow-x-auto" aria-busy={loading || undefined}>
      <table className="w-full border-collapse text-sm">
        <thead>
          {headerGroups.map((headerGroup) => (
            <tr key={headerGroup.id} className="border-b border-default">
              {headerGroup.headers.map((header) => {
                const canSort = sortable && header.column.getCanSort();
                const sortDir = header.column.getIsSorted();
                const ariaSort =
                  sortDir === "asc"
                    ? "ascending"
                    : sortDir === "desc"
                      ? "descending"
                      : "none";
                return (
                  <th
                    key={header.id}
                    scope="col"
                    aria-sort={canSort ? ariaSort : undefined}
                    className={cn(
                      "text-left font-semibold text-secondary",
                      pad,
                    )}
                  >
                    {header.isPlaceholder ? null : canSort ? (
                      <button
                        type="button"
                        onClick={header.column.getToggleSortingHandler()}
                        className={cn(
                          "inline-flex items-center gap-1 font-semibold text-secondary",
                          "transition-colors duration-150 hover:text-primary",
                          "focus-visible:outline-none focus-visible:shadow-focus-ring rounded-sm",
                        )}
                      >
                        {flexRender(
                          header.column.columnDef.header,
                          header.getContext(),
                        )}
                        {sortDir === "asc" ? (
                          <ChevronUp className="size-3.5" aria-hidden="true" />
                        ) : sortDir === "desc" ? (
                          <ChevronDown className="size-3.5" aria-hidden="true" />
                        ) : null}
                      </button>
                    ) : (
                      flexRender(
                        header.column.columnDef.header,
                        header.getContext(),
                      )
                    )}
                  </th>
                );
              })}
            </tr>
          ))}
        </thead>
        <tbody>
          {loading
            ? Array.from({ length: SKELETON_ROWS }, (_, rowIndex) => (
                <tr key={`skeleton-${rowIndex}`} className="border-b border-default">
                  {columns.map((_, colIndex) => (
                    <td key={`skeleton-cell-${colIndex}`} className={pad}>
                      <div className="h-4 w-full animate-pulse rounded-sm bg-skeleton" />
                    </td>
                  ))}
                </tr>
              ))
            : isEmpty
              ? (
                  <tr>
                    <td
                      colSpan={columns.length}
                      className={cn("text-center text-tertiary", pad)}
                    >
                      {emptyState ?? "Нет данных"}
                    </td>
                  </tr>
                )
              : rows.map((row) => (
                  <tr
                    key={row.id}
                    className="border-b border-default transition-colors duration-150 hover:bg-surface"
                  >
                    {row.getVisibleCells().map((cell) => (
                      <td key={cell.id} className={cn("text-primary", pad)}>
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    ))}
                  </tr>
                ))}
        </tbody>
      </table>
    </div>
  );
}
