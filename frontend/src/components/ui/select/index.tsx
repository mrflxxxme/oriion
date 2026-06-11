/**
 * Select — single-select dropdown (component-inventory.md #7).
 * Wraps @radix-ui/react-select. Multi-select is Wave-1 — single value only here.
 */
import { forwardRef } from "react";
import type { ElementRef } from "react";
import * as SelectPrimitive from "@radix-ui/react-select";
import { Check, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

export interface SelectOption {
  label: string;
  value: string;
  disabled?: boolean;
}

export interface SelectProps {
  options: SelectOption[];
  placeholder?: string;
  value?: string;
  defaultValue?: string;
  onValueChange?: (value: string) => void;
  disabled?: boolean;
  invalid?: boolean;
  name?: string;
  "aria-label"?: string;
  "aria-labelledby"?: string;
  id?: string;
  className?: string;
}

export const Select = forwardRef<
  ElementRef<typeof SelectPrimitive.Trigger>,
  SelectProps
>(function Select(
  {
    options,
    placeholder,
    value,
    defaultValue,
    onValueChange,
    disabled = false,
    invalid = false,
    name,
    id,
    className,
    ...aria
  },
  ref,
) {
  return (
    <SelectPrimitive.Root
      {...(value !== undefined ? { value } : {})}
      {...(defaultValue !== undefined ? { defaultValue } : {})}
      {...(onValueChange ? { onValueChange } : {})}
      disabled={disabled}
      {...(name !== undefined ? { name } : {})}
    >
      <SelectPrimitive.Trigger
        ref={ref}
        id={id}
        aria-invalid={invalid || undefined}
        className={cn(
          "flex h-10 w-full items-center justify-between gap-2 bg-surface text-primary border rounded-sm px-3 transition-colors duration-150 focus-visible:outline-none focus-visible:shadow-focus-ring disabled:cursor-not-allowed disabled:opacity-50 data-[placeholder]:text-tertiary",
          invalid ? "border-danger-600" : "border-default",
          className,
        )}
        {...aria}
      >
        <SelectPrimitive.Value placeholder={placeholder} />
        <SelectPrimitive.Icon asChild>
          <ChevronDown className="size-4 text-tertiary" aria-hidden="true" />
        </SelectPrimitive.Icon>
      </SelectPrimitive.Trigger>
      <SelectPrimitive.Portal>
        <SelectPrimitive.Content
          position="popper"
          sideOffset={4}
          className="z-dropdown min-w-[var(--radix-select-trigger-width)] overflow-hidden bg-surface text-primary border border-default rounded-md shadow-md"
        >
          <SelectPrimitive.Viewport className="p-1">
            {options.map((option) => (
              <SelectPrimitive.Item
                key={option.value}
                value={option.value}
                disabled={option.disabled ?? false}
                className="relative flex cursor-pointer select-none items-center gap-2 rounded-sm py-2 pl-8 pr-3 text-sm outline-none data-[highlighted]:bg-page data-[highlighted]:outline-none data-[disabled]:pointer-events-none data-[disabled]:opacity-50"
              >
                <SelectPrimitive.ItemIndicator className="absolute left-2 inline-flex items-center">
                  <Check className="size-4 text-cta" aria-hidden="true" />
                </SelectPrimitive.ItemIndicator>
                <SelectPrimitive.ItemText>{option.label}</SelectPrimitive.ItemText>
              </SelectPrimitive.Item>
            ))}
          </SelectPrimitive.Viewport>
        </SelectPrimitive.Content>
      </SelectPrimitive.Portal>
    </SelectPrimitive.Root>
  );
});
