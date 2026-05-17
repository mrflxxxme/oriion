import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Объединяет class-names с дедупликацией Tailwind utility-классов.
 *
 * Стандартный shadcn/ui helper для условного выставления классов
 * без конфликтов между Tailwind utilities.
 *
 * @example
 *   cn("px-4 py-2", isActive && "bg-primary", "px-6")
 *   // → "py-2 bg-primary px-6"  (px-4 побеждается px-6, как и должно)
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
