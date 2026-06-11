/**
 * Toast — transient corner notification (component-inventory.md #9).
 * Thin wrapper over the `sonner` library, styled with our Nordic Warm tokens.
 *
 * Usage:
 *   Mount <Toaster /> once near the app root, then call the `toast` helper
 *   anywhere: `toast.success("Сохранено")`, `toast.error("Ошибка")`.
 *
 * sonner sets role=status (info/success) / role=alert (warning/danger) and
 * honours prefers-reduced-motion internally, so we only own the visual theme.
 */
import { Toaster as SonnerToaster, toast as sonnerToast } from "sonner";
import type { ToasterProps } from "sonner";

/**
 * Token-driven classNames for every toast surface. We avoid sonner's
 * `richColors` so the palette stays on our semantic tokens.
 */
const toastClassNames = {
  toast: "group bg-surface text-primary border border-default rounded-md shadow-lg text-sm",
  title: "font-medium text-primary",
  description: "text-secondary",
  actionButton: "bg-cta text-on-cta rounded-sm font-medium",
  cancelButton: "bg-surface text-secondary rounded-sm",
  closeButton: "bg-surface text-secondary border border-default",
} as const;

export type { ToasterProps };

/**
 * Pre-configured sonner Toaster: bottom-right, our tokens, no rich colors.
 * Extra props (e.g. `theme`, `expand`) pass straight through.
 */
export function Toaster(props: ToasterProps) {
  return (
    <SonnerToaster
      position="bottom-right"
      richColors={false}
      toastOptions={{ classNames: toastClassNames }}
      {...props}
    />
  );
}

/**
 * Variant-aware helper around sonner's `toast`. Calling `toast(msg)` shows a
 * neutral toast; the variant methods map to sonner's semantic calls.
 */
// eslint-disable-next-line react-refresh/only-export-components -- toast helper co-located with Toaster per shadcn convention
export const toast = Object.assign((message: string) => sonnerToast(message), {
  success: (message: string) => sonnerToast.success(message),
  error: (message: string) => sonnerToast.error(message),
  info: (message: string) => sonnerToast.info(message),
  warning: (message: string) => sonnerToast.warning(message),
  dismiss: (id?: string | number) => sonnerToast.dismiss(id),
});
