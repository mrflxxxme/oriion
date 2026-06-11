/**
 * Shared formatting helpers for the cells feature.
 */
import { t } from "@/lib/i18n";

const dateFmt = new Intl.DateTimeFormat("ru-RU", { dateStyle: "medium" });

/** Format an ISO date string as ru-RU medium; guard missing/invalid input. */
export function formatDate(value: string | null | undefined): string {
  if (!value) return t("cells.dash");
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return t("cells.dash");
  return dateFmt.format(date);
}
