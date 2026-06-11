/**
 * Card — surface container (component-inventory.md #2).
 * Compound component: Card + Card.Header / Card.Body / Card.Footer.
 */
import { forwardRef } from "react";
import type { HTMLAttributes } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const cardVariants = cva("bg-surface rounded-lg transition-colors duration-150", {
  variants: {
    variant: {
      default: "",
      elevated: "shadow-md",
      outlined: "border border-default",
    },
    interactive: {
      true: "cursor-pointer hover:shadow-sm focus-visible:outline-none focus-visible:shadow-focus-ring",
      false: "",
    },
  },
  defaultVariants: { variant: "default", interactive: false },
});

const paddingClass = {
  none: "p-0",
  sm: "p-4",
  md: "p-6",
  lg: "p-8",
} as const;

export interface CardProps
  extends HTMLAttributes<HTMLDivElement>, Omit<VariantProps<typeof cardVariants>, "interactive"> {
  padding?: "sm" | "md" | "lg" | "none";
  interactive?: boolean;
}

const CardRoot = forwardRef<HTMLDivElement, CardProps>(function Card(
  { className, variant, padding = "md", interactive = false, ...props },
  ref,
) {
  // `default` variant has no border; ensure it still reads as a surface block.
  const variantClass = variant ?? "default";
  const interactiveProps = interactive ? ({ role: "button", tabIndex: 0 } as const) : {};
  return (
    <div
      ref={ref}
      className={cn(
        cardVariants({ variant: variantClass, interactive }),
        paddingClass[padding],
        className,
      )}
      {...interactiveProps}
      {...props}
    />
  );
});

const CardHeader = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(function CardHeader(
  { className, ...props },
  ref,
) {
  return <div ref={ref} className={cn("flex flex-col gap-1 text-primary", className)} {...props} />;
});

const CardBody = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(function CardBody(
  { className, ...props },
  ref,
) {
  return <div ref={ref} className={cn("text-secondary", className)} {...props} />;
});

const CardFooter = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(function CardFooter(
  { className, ...props },
  ref,
) {
  return <div ref={ref} className={cn("flex items-center gap-2", className)} {...props} />;
});

export const Card = Object.assign(CardRoot, {
  Header: CardHeader,
  Body: CardBody,
  Footer: CardFooter,
});
