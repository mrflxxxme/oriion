/**
 * Button — primary interactive element (component-inventory.md #4).
 * shadcn-style cva variants over a native <button>, Radix Slot for `asChild`.
 */
import { forwardRef } from "react";
import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

// eslint-disable-next-line react-refresh/only-export-components -- cva helper co-located per shadcn convention
export const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors duration-150 focus-visible:outline-none focus-visible:shadow-focus-ring disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        primary: "bg-cta text-on-cta hover:bg-brand-700",
        secondary: "bg-surface text-primary border border-default hover:border-emphasis",
        ghost: "text-primary hover:bg-surface",
        destructive: "bg-danger-600 text-on-danger hover:bg-danger-700",
        link: "text-cta-hover underline-offset-4 hover:underline",
      },
      size: {
        sm: "h-8 px-3 text-xs",
        md: "h-10 px-4",
        lg: "h-12 px-6 text-base",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);

export interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {
  /** Render the child as the button (Radix Slot) — e.g. wrap a router <Link>. */
  asChild?: boolean;
  /** Show a spinner + set aria-busy; also disables interaction. */
  loading?: boolean;
  iconLeft?: ReactNode;
  iconRight?: ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { className, variant, size, asChild, loading, iconLeft, iconRight, children, disabled, ...props },
  ref,
) {
  // Radix Slot requires a single child — when `asChild`, pass children through
  // untouched (icon/spinner decoration only applies to the native button).
  if (asChild) {
    return (
      <Slot
        ref={ref}
        className={cn(buttonVariants({ variant, size }), className)}
        aria-busy={loading ?? undefined}
        {...props}
      >
        {children}
      </Slot>
    );
  }
  return (
    <button
      ref={ref}
      className={cn(buttonVariants({ variant, size }), className)}
      disabled={disabled ?? loading}
      aria-busy={loading ?? undefined}
      {...props}
    >
      {loading ? <Loader2 className="size-4 animate-spin" aria-hidden="true" /> : iconLeft}
      {children}
      {iconRight}
    </button>
  );
});
