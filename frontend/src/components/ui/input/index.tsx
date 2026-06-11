/**
 * Input — native text input wrapper (component-inventory.md #5).
 * cva sizing; optional prefix/suffix adornments rendered in a flex wrapper.
 */
import { forwardRef } from "react";
import type { InputHTMLAttributes, ReactNode } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const inputVariants = cva(
  "w-full bg-surface text-primary border rounded-sm transition-colors duration-150 placeholder:text-tertiary focus-visible:outline-none focus-visible:shadow-focus-ring disabled:cursor-not-allowed disabled:opacity-50",
  {
    variants: {
      size: {
        sm: "h-8 px-3 text-sm",
        md: "h-10 px-3",
        lg: "h-12 px-4 text-base",
      },
      invalid: {
        true: "border-danger-600",
        false: "border-default",
      },
    },
    defaultVariants: { size: "md", invalid: false },
  },
);

export interface InputProps
  // native input has a numeric `size` attr and a string `prefix` global attr —
  // omit both so our variant `size` and ReactNode `prefix`/`suffix` win.
  extends Omit<InputHTMLAttributes<HTMLInputElement>, "size" | "prefix">,
    Omit<VariantProps<typeof inputVariants>, "invalid"> {
  invalid?: boolean;
  prefix?: ReactNode;
  suffix?: ReactNode;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { className, size, invalid = false, prefix, suffix, ...props },
  ref,
) {
  const control = (
    <input
      ref={ref}
      aria-invalid={invalid || undefined}
      className={cn(
        inputVariants({ size, invalid }),
        // Strip the box styling when adorned — the wrapper owns the border.
        (prefix || suffix) && "h-auto border-0 bg-transparent px-0 focus-visible:shadow-none",
        className,
      )}
      {...props}
    />
  );

  if (!prefix && !suffix) return control;

  return (
    <div
      className={cn(
        "flex items-center gap-2 bg-surface border rounded-sm transition-colors duration-150 focus-within:shadow-focus-ring",
        invalid ? "border-danger-600" : "border-default",
        size === "sm" ? "h-8 px-3" : size === "lg" ? "h-12 px-4" : "h-10 px-3",
      )}
    >
      {prefix ? <span className="text-tertiary shrink-0">{prefix}</span> : null}
      {control}
      {suffix ? <span className="text-tertiary shrink-0">{suffix}</span> : null}
    </div>
  );
});
