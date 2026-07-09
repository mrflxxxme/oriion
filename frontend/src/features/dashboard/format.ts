/**
 * Dashboard formatting helpers.
 */
import { t } from "@/lib/i18n";

const dateFmt = new Intl.DateTimeFormat("ru-RU", { dateStyle: "medium", timeStyle: "short" });

/** Format an ISO date string as ru-RU medium+short; guard missing/invalid. */
export function formatDateTime(value: string | null | undefined): string {
  if (!value) return t("cells.dash");
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return t("cells.dash");
  return dateFmt.format(date);
}

/**
 * Format a decimal-string credit amount (backend emits credits as strings) to
 * a fixed 2-dp ru-RU number. Falls back to the raw value when unparseable so a
 * surprising backend shape never renders as "NaN".
 */
export function formatCredits(value: string | null | undefined): string {
  if (value === null || value === undefined) return t("cells.dash");
  const parsed = Number(value);
  if (Number.isNaN(parsed)) return value;
  return parsed.toLocaleString("ru-RU", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
