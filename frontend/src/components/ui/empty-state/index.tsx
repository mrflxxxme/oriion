/**
 * EmptyState — communicates absence of data with a next action
 * (component-inventory.md #11). Centered column: optional illustration,
 * required title, optional description, optional CTA button.
 *
 * `variant="danger"` colours the title accent and defaults to an AlertTriangle
 * icon when no custom illustration is supplied (error / failure states).
 */
import { forwardRef } from "react";
import type { HTMLAttributes, ReactNode } from "react";
import { AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

export interface EmptyStateAction {
  label: string;
  onClick: () => void;
}

export interface EmptyStateProps extends HTMLAttributes<HTMLDivElement> {
  /** Decorative visual above the title; rendered with aria-hidden. */
  illustration?: ReactNode;
  /** Required headline. */
  title: string;
  /** Supporting copy under the title. */
  description?: string;
  /** Primary CTA — renders the shared Button. */
  action?: EmptyStateAction;
  /** `danger` for error states (accent colour + default warning icon). */
  variant?: "default" | "danger";
}

export const EmptyState = forwardRef<HTMLDivElement, EmptyStateProps>(
  function EmptyState(
    { className, illustration, title, description, action, variant = "default", ...props },
    ref,
  ) {
    const isDanger = variant === "danger";
    // Fall back to a tone-appropriate icon when no illustration is provided.
    const visual =
      illustration ??
      (isDanger ? (
        <AlertTriangle className="size-10 text-danger-600" />
      ) : null);

    return (
      <div
        ref={ref}
        className={cn(
          "flex flex-col items-center justify-center gap-3 px-6 py-12 text-center",
          className,
        )}
        {...props}
      >
        {visual ? (
          <div className="mb-1 text-tertiary" aria-hidden="true">
            {visual}
          </div>
        ) : null}
        <h3
          className={cn(
            "text-lg font-medium",
            isDanger ? "text-danger-600" : "text-primary",
          )}
        >
          {title}
        </h3>
        {description ? (
          <p className="max-w-sm text-sm text-secondary">{description}</p>
        ) : null}
        {action ? (
          <Button
            variant={isDanger ? "destructive" : "primary"}
            onClick={action.onClick}
            className="mt-2"
          >
            {action.label}
          </Button>
        ) : null}
      </div>
    );
  },
);
