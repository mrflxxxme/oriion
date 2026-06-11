/**
 * Breadcrumb — hierarchical navigation trail (component-inventory.md #17).
 * Custom semantic <nav><ol>; collapses the middle to «…» past `maxItems`.
 * Router wiring is the consumer's job — links render as plain <a href>.
 */
import { forwardRef } from "react";
import type { HTMLAttributes, ReactNode } from "react";
import { ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

export interface BreadcrumbItem {
  label: string;
  href?: string;
}

export interface BreadcrumbProps extends HTMLAttributes<HTMLElement> {
  items: BreadcrumbItem[];
  separator?: ReactNode;
  /** Max visible crumbs before the middle collapses to an ellipsis (default 4). */
  maxItems?: number;
}

const ELLIPSIS = "…";

/** Collapse the middle when `items` exceeds `maxItems`: keep first + last (maxItems-1). */
function collapse(items: BreadcrumbItem[], maxItems: number): (BreadcrumbItem | null)[] {
  if (items.length <= maxItems) return items;
  const first = items[0];
  const tail = items.slice(items.length - (maxItems - 1));
  return first ? [first, null, ...tail] : [null, ...tail];
}

export const Breadcrumb = forwardRef<HTMLElement, BreadcrumbProps>(function Breadcrumb(
  { className, items, separator, maxItems = 4, ...props },
  ref,
) {
  const sep = separator ?? <ChevronRight className="size-4" aria-hidden="true" />;
  const visible = collapse(items, maxItems);
  const lastIndex = visible.length - 1;

  return (
    <nav ref={ref} aria-label="Breadcrumb" className={className} {...props}>
      <ol className="flex flex-wrap items-center gap-2 text-sm">
        {visible.map((item, index) => {
          const isLast = index === lastIndex;
          return (
            <li key={item ? `${item.label}-${index}` : `ellipsis-${index}`} className="flex items-center gap-2">
              {item === null ? (
                <span className="text-tertiary" aria-hidden="true">
                  {ELLIPSIS}
                </span>
              ) : isLast ? (
                <span aria-current="page" className="font-medium text-primary">
                  {item.label}
                </span>
              ) : item.href ? (
                <a
                  href={item.href}
                  className={cn(
                    "text-secondary transition-colors duration-150 hover:text-primary",
                    "focus-visible:outline-none focus-visible:shadow-focus-ring rounded-sm",
                  )}
                >
                  {item.label}
                </a>
              ) : (
                <span className="text-secondary">{item.label}</span>
              )}
              {!isLast ? <span aria-hidden="true" className="text-tertiary">{sep}</span> : null}
            </li>
          );
        })}
      </ol>
    </nav>
  );
});
