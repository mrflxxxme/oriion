/**
 * RadioGroup — single-choice group (component-inventory.md #8b).
 * Wraps @radix-ui/react-radio-group; Radix supplies role=radiogroup.
 */
import { forwardRef, useId } from "react";
import type { ComponentRef } from "react";
import * as RadioGroupPrimitive from "@radix-ui/react-radio-group";
import { cn } from "@/lib/utils";

export interface RadioOption {
  label: string;
  value: string;
  disabled?: boolean;
}

export interface RadioGroupProps {
  options: RadioOption[];
  value?: string;
  defaultValue?: string;
  onValueChange?: (value: string) => void;
  name?: string;
  disabled?: boolean;
  className?: string;
  "aria-label"?: string;
  "aria-labelledby"?: string;
}

export const RadioGroup = forwardRef<
  ComponentRef<typeof RadioGroupPrimitive.Root>,
  RadioGroupProps
>(function RadioGroup(
  { options, value, defaultValue, onValueChange, name, disabled = false, className, ...aria },
  ref,
) {
  const baseId = useId();
  return (
    <RadioGroupPrimitive.Root
      ref={ref}
      {...(value !== undefined ? { value } : {})}
      {...(defaultValue !== undefined ? { defaultValue } : {})}
      {...(onValueChange ? { onValueChange } : {})}
      {...(name !== undefined ? { name } : {})}
      disabled={disabled}
      className={cn("flex flex-col gap-2", className)}
      {...aria}
    >
      {options.map((option) => {
        const itemId = `${baseId}-${option.value}`;
        return (
          <span key={option.value} className="inline-flex items-center gap-2">
            <RadioGroupPrimitive.Item
              id={itemId}
              value={option.value}
              disabled={option.disabled ?? false}
              className="size-5 shrink-0 bg-surface border border-default rounded-full transition-colors duration-150 focus-visible:outline-none focus-visible:shadow-focus-ring disabled:cursor-not-allowed disabled:opacity-50 data-[state=checked]:border-cta"
            >
              <RadioGroupPrimitive.Indicator className="flex items-center justify-center after:block after:size-2.5 after:rounded-full after:bg-cta" />
            </RadioGroupPrimitive.Item>
            <label htmlFor={itemId} className="text-sm text-primary cursor-pointer select-none">
              {option.label}
            </label>
          </span>
        );
      })}
    </RadioGroupPrimitive.Root>
  );
});
