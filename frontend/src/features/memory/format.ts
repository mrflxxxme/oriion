/**
 * Shared formatting helpers for the memory feature.
 * (Small, deliberately not shared with `features/cells/format.ts` — a
 * cross-feature import there would couple two independent feature folders
 * for a two-line date formatter.)
 */
const dateTimeFmt = new Intl.DateTimeFormat("ru-RU", { dateStyle: "medium", timeStyle: "short" });

/** Format an ISO date-time string as ru-RU medium date + short time. */
export function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return dateTimeFmt.format(date);
}
