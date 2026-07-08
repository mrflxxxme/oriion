/**
 * Human-readable labels for the memory `kind` / `source` enums — pulled out
 * of `MemoryEntryList.tsx` so that component file only exports components
 * (react-refresh/only-export-components).
 */
import type { BadgeProps } from "@/components/ui";
import { t } from "@/lib/i18n";

const KIND_LABELS: Record<string, string> = {
  fact: t("memory.kind.fact"),
  note: t("memory.kind.note"),
  glossary: t("memory.kind.glossary"),
  preference: t("memory.kind.preference"),
  style: t("memory.kind.style"),
  process: t("memory.kind.process"),
};

const SOURCE_BADGE: Record<string, { variant: BadgeProps["variant"]; label: string }> = {
  manual: { variant: "default", label: t("memory.source.manual") },
  filter_agent: { variant: "info", label: t("memory.source.filter_agent") },
  summary: { variant: "warning", label: t("memory.source.summary") },
};

/** Human label for a memory `kind` — falls back to the raw value for kinds
 * with no copy yet (e.g. the system-generated `conversation_summary`). */
export function kindLabel(kind: string): string {
  return KIND_LABELS[kind] ?? kind;
}

/** Badge variant + label for a memory `source`. */
export function sourceBadge(source: string): { variant: BadgeProps["variant"]; label: string } {
  return SOURCE_BADGE[source] ?? { variant: "default", label: source };
}
