/**
 * Separator — thin visual/semantic divider (component-inventory.md #3).
 * Wraps @radix-ui/react-separator; decorative by default (aria-hidden).
 */
import { forwardRef } from "react";
import type { ComponentPropsWithoutRef, ComponentRef } from "react";
import * as SeparatorPrimitive from "@radix-ui/react-separator";
import { cn } from "@/lib/utils";

export interface SeparatorProps extends Omit<
  ComponentPropsWithoutRef<typeof SeparatorPrimitive.Root>,
  "orientation"
> {
  orientation?: "horizontal" | "vertical";
  decorative?: boolean;
}

export const Separator = forwardRef<ComponentRef<typeof SeparatorPrimitive.Root>, SeparatorProps>(
  function Separator({ className, orientation = "horizontal", decorative = true, ...props }, ref) {
    return (
      <SeparatorPrimitive.Root
        ref={ref}
        decorative={decorative}
        orientation={orientation}
        // `bg-default` maps to --border-default (index.css §--color-default).
        className={cn(
          "shrink-0 bg-default",
          orientation === "horizontal" ? "h-px w-full" : "h-full w-px",
          className,
        )}
        {...props}
      />
    );
  },
);
