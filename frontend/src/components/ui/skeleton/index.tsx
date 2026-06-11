/**
 * Skeleton — loading placeholder (component-inventory.md #12).
 * `bg-skeleton animate-pulse`; reduced-motion suppression is handled globally
 * in index.css. Bars are decorative (`aria-hidden`); the PARENT region owns
 * `aria-busy="true"` since a skeleton is usually a child of the loading area.
 */
import { forwardRef } from "react";
import type { CSSProperties, HTMLAttributes } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const skeletonVariants = cva("bg-skeleton animate-pulse", {
  variants: {
    variant: {
      text: "rounded-sm h-4",
      circular: "rounded-full",
      rectangular: "rounded-sm",
    },
  },
  defaultVariants: { variant: "rectangular" },
});

export interface SkeletonProps
  extends HTMLAttributes<HTMLDivElement>, VariantProps<typeof skeletonVariants> {
  /** Number of stacked bars for the `text` variant. */
  lines?: number;
  /** Explicit width — dynamic data, so applied via inline style. */
  width?: string | number;
  /** Explicit height — dynamic data, so applied via inline style. */
  height?: string | number;
}

/** Build an inline-style object only for the dimensions that were provided. */
function dimensionStyle(
  width: string | number | undefined,
  height: string | number | undefined,
): CSSProperties | undefined {
  if (width === undefined && height === undefined) return undefined;
  return {
    ...(width !== undefined && { width }),
    ...(height !== undefined && { height }),
  };
}

export const Skeleton = forwardRef<HTMLDivElement, SkeletonProps>(function Skeleton(
  { className, variant = "rectangular", lines = 1, width, height, style, ...props },
  ref,
) {
  // Dimensions are dynamic content, so they must live in inline style.
  const dims = dimensionStyle(width, height);
  const mergedStyle: CSSProperties | undefined = dims || style ? { ...dims, ...style } : undefined;

  if (variant === "text" && lines > 1) {
    return (
      <div ref={ref} className={cn("flex flex-col gap-2", className)} {...props}>
        {Array.from({ length: lines }, (_, i) => (
          <div
            key={i}
            aria-hidden="true"
            className={cn(
              skeletonVariants({ variant: "text" }),
              // Last line is shorter for a natural paragraph rhythm.
              i === lines - 1 && "w-3/4",
            )}
            style={mergedStyle ?? undefined}
          />
        ))}
      </div>
    );
  }

  return (
    <div
      ref={ref}
      aria-hidden="true"
      className={cn(skeletonVariants({ variant }), className)}
      style={mergedStyle ?? undefined}
      {...props}
    />
  );
});
