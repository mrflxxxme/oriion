/**
 * Checkbox — boolean / tri-state control (component-inventory.md #8a).
 * Wraps @radix-ui/react-checkbox; optional `label` renders a linked <label>.
 */
import { forwardRef } from "react";
import type { ComponentPropsWithoutRef, ComponentRef } from "react";
import * as CheckboxPrimitive from "@radix-ui/react-checkbox";
import { Check, Minus } from "lucide-react";
import { cn } from "@/lib/utils";

export interface CheckboxProps extends ComponentPropsWithoutRef<typeof CheckboxPrimitive.Root> {
  /** Convenience label rendered next to the box and linked via htmlFor. */
  label?: string;
}

export const Checkbox = forwardRef<ComponentRef<typeof CheckboxPrimitive.Root>, CheckboxProps>(
  function Checkbox({ className, label, id, checked, ...props }, ref) {
    const box = (
      <CheckboxPrimitive.Root
        ref={ref}
        id={id}
        {...(checked !== undefined ? { checked } : {})}
        className={cn(
          "peer size-5 shrink-0 bg-surface border border-default rounded-sm transition-colors duration-150 focus-visible:outline-none focus-visible:shadow-focus-ring disabled:cursor-not-allowed disabled:opacity-50 data-[state=checked]:bg-cta data-[state=checked]:text-on-cta data-[state=indeterminate]:bg-cta data-[state=indeterminate]:text-on-cta",
          className,
        )}
        {...props}
      >
        <CheckboxPrimitive.Indicator className="flex items-center justify-center">
          {checked === "indeterminate" ? (
            <Minus className="size-4" aria-hidden="true" />
          ) : (
            <Check className="size-4" aria-hidden="true" />
          )}
        </CheckboxPrimitive.Indicator>
      </CheckboxPrimitive.Root>
    );

    if (!label) return box;

    return (
      <span className="inline-flex items-center gap-2">
        {box}
        <label htmlFor={id} className="text-sm text-primary cursor-pointer select-none">
          {label}
        </label>
      </span>
    );
  },
);
