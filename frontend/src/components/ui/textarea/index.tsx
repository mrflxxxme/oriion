/**
 * Textarea — native multiline input wrapper (component-inventory.md #6).
 * Optional autosize (grow to content) + live character counter when maxLength set.
 */
import { forwardRef, useCallback, useRef } from "react";
import type { ChangeEvent, InputEvent, TextareaHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export interface TextareaProps
  extends Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, "rows"> {
  rows?: number;
  autosize?: boolean;
  invalid?: boolean;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  function Textarea(
    { className, rows = 4, autosize = false, invalid = false, maxLength, value, onInput, ...props },
    ref,
  ) {
    const innerRef = useRef<HTMLTextAreaElement | null>(null);

    const setRefs = useCallback(
      (node: HTMLTextAreaElement | null) => {
        innerRef.current = node;
        if (typeof ref === "function") ref(node);
        else if (ref) ref.current = node;
      },
      [ref],
    );

    const handleInput = useCallback(
      (e: InputEvent<HTMLTextAreaElement>) => {
        if (autosize) {
          const el = e.currentTarget;
          // Inline style is the documented exception for autosize: we must read
          // scrollHeight and write it back to the element height each input.
          el.style.height = "auto";
          el.style.height = `${el.scrollHeight}px`;
        }
        onInput?.(e);
      },
      [autosize, onInput],
    );

    // Counter is controlled-only: read the length from the `value` prop.
    const currentLength = typeof value === "string" ? value.length : 0;

    return (
      <div className="flex flex-col gap-1">
        <textarea
          ref={setRefs}
          rows={rows}
          maxLength={maxLength}
          aria-invalid={invalid || undefined}
          onInput={handleInput}
          {...(value !== undefined ? { value } : {})}
          className={cn(
            "w-full bg-surface text-primary border rounded-sm px-3 py-2 transition-colors duration-150 placeholder:text-tertiary focus-visible:outline-none focus-visible:shadow-focus-ring disabled:cursor-not-allowed disabled:opacity-50",
            autosize && "resize-none overflow-hidden",
            invalid ? "border-danger-600" : "border-default",
            className,
          )}
          {...(props as Omit<TextareaProps, "value">)}
        />
        {maxLength !== undefined ? (
          <span className="text-xs text-tertiary self-end" aria-live="polite">
            {currentLength}/{maxLength}
          </span>
        ) : null}
      </div>
    );
  },
);

// Re-export the change handler type for consumers wiring controlled state.
export type TextareaChangeHandler = (e: ChangeEvent<HTMLTextAreaElement>) => void;
