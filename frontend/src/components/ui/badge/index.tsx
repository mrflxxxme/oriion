/**
 * Badge — compact status/label pill (component-inventory.md #14).
 * cva variants over a native <span>; colour is never the sole signal —
 * the consumer is responsible for accompanying text context.
 */
import { forwardRef } from "react";
import type { HTMLAttributes } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

// eslint-disable-next-line react-refresh/only-export-components -- cva helper co-located per shadcn convention
export const badgeVariants = cva(
  "inline-flex items-center rounded-full font-medium tracking-wide whitespace-nowrap",
  {
    variants: {
      variant: {
        default: "bg-surface text-secondary border border-default",
        primary: "bg-brand-100 text-brand-700",
        success: "bg-success-100 text-success-700",
        warning: "bg-warning-100 text-warning-700",
        danger: "bg-danger-100 text-danger-700",
        info: "bg-info-100 text-info-700",
      },
      size: {
        sm: "px-2 py-0.5 text-xs",
        md: "px-2.5 py-1 text-sm",
      },
    },
    defaultVariants: { variant: "default", size: "sm" },
  },
);

export interface BadgeProps
  extends HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {}

export const Badge = forwardRef<HTMLSpanElement, BadgeProps>(function Badge(
  { className, variant, size, ...props },
  ref,
) {
  return <span ref={ref} className={cn(badgeVariants({ variant, size }), className)} {...props} />;
});
