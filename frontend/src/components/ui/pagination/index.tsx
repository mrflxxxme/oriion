/**
 * Pagination — windowed page navigation (component-inventory.md #18).
 * Custom semantic <nav> reusing the Button primitive for every control.
 * Renders nothing when there is a single page (or fewer).
 */
import { forwardRef } from "react";
import type { HTMLAttributes } from "react";
import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export interface PaginationProps extends Omit<HTMLAttributes<HTMLElement>, "onChange"> {
  currentPage: number;
  totalPages: number;
  pageSize?: number;
  onPageChange: (page: number) => void;
  showFirstLast?: boolean;
}

const ELLIPSIS = "ellipsis";

/** Windowed page list: first, last, current ±1, with ellipses where gaps occur. */
function buildPages(current: number, total: number): (number | typeof ELLIPSIS)[] {
  if (total <= 7) {
    return Array.from({ length: total }, (_, i) => i + 1);
  }
  const pages: (number | typeof ELLIPSIS)[] = [1];
  const start = Math.max(2, current - 1);
  const end = Math.min(total - 1, current + 1);
  if (start > 2) pages.push(ELLIPSIS);
  for (let p = start; p <= end; p++) pages.push(p);
  if (end < total - 1) pages.push(ELLIPSIS);
  pages.push(total);
  return pages;
}

export const Pagination = forwardRef<HTMLElement, PaginationProps>(function Pagination(
  {
    className,
    currentPage,
    totalPages,
    pageSize: _pageSize,
    onPageChange,
    showFirstLast = true,
    ...props
  },
  ref,
) {
  if (totalPages <= 1) return null;

  const atStart = currentPage <= 1;
  const atEnd = currentPage >= totalPages;
  const pages = buildPages(currentPage, totalPages);

  return (
    <nav
      ref={ref}
      aria-label="Pagination"
      className={cn("flex items-center gap-1", className)}
      {...props}
    >
      {showFirstLast ? (
        <Button
          variant="ghost"
          size="icon"
          aria-label="Первая страница"
          disabled={atStart}
          aria-disabled={atStart}
          onClick={() => {
            onPageChange(1);
          }}
        >
          <ChevronsLeft className="size-4" aria-hidden="true" />
        </Button>
      ) : null}
      <Button
        variant="ghost"
        size="icon"
        aria-label="Предыдущая страница"
        disabled={atStart}
        aria-disabled={atStart}
        onClick={() => {
          onPageChange(currentPage - 1);
        }}
      >
        <ChevronLeft className="size-4" aria-hidden="true" />
      </Button>

      {pages.map((page, index) =>
        page === ELLIPSIS ? (
          <span
            key={`ellipsis-${String(index)}`}
            aria-hidden="true"
            className="px-2 text-sm text-tertiary"
          >
            …
          </span>
        ) : (
          <Button
            key={page}
            variant="ghost"
            size="sm"
            aria-label={`Страница ${String(page)}`}
            aria-current={page === currentPage ? "page" : undefined}
            className={cn("min-w-8", page === currentPage && "bg-cta text-on-cta hover:bg-cta")}
            onClick={() => {
              onPageChange(page);
            }}
          >
            {page}
          </Button>
        ),
      )}

      <Button
        variant="ghost"
        size="icon"
        aria-label="Следующая страница"
        disabled={atEnd}
        aria-disabled={atEnd}
        onClick={() => {
          onPageChange(currentPage + 1);
        }}
      >
        <ChevronRight className="size-4" aria-hidden="true" />
      </Button>
      {showFirstLast ? (
        <Button
          variant="ghost"
          size="icon"
          aria-label="Последняя страница"
          disabled={atEnd}
          aria-disabled={atEnd}
          onClick={() => {
            onPageChange(totalPages);
          }}
        >
          <ChevronsRight className="size-4" aria-hidden="true" />
        </Button>
      ) : null}
    </nav>
  );
});
