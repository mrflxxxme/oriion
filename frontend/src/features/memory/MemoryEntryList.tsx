/**
 * MemoryEntryList — shared read/delete surface for cell- and role-memory
 * entries. `DisplayMemoryEntry` is a structural subset both `MemoryEntry`
 * and `RoleMemoryEntry` (api/memory.ts) satisfy, so this one component
 * serves both the "Ячейка" and "Агент" tabs, for both the plain list and
 * search-hit rendering (via the optional per-item `score`).
 *
 * A single Dialog instance (not one per row) confirms deletion — Radix
 * Dialog owns the focus trap / Esc / focus-restore.
 */
import { useState } from "react";
import { Badge, Button, Dialog } from "@/components/ui";
import { t } from "@/lib/i18n";
import { formatDateTime } from "./format";
import { kindLabel, sourceBadge } from "./labels";

export interface DisplayMemoryEntry {
  id: string;
  kind: string;
  title: string | null;
  content: string;
  source: string;
  created_at: string;
}

export interface MemoryListItem {
  entry: DisplayMemoryEntry;
  /** Cosine similarity in [-1, 1] — set only when rendering search hits. */
  score?: number;
}

interface MemoryEntryRowProps {
  entry: DisplayMemoryEntry;
  score?: number;
  onRequestDelete: (entryId: string) => void;
}

function MemoryEntryRow({ entry, score, onRequestDelete }: MemoryEntryRowProps) {
  const badge = sourceBadge(entry.source);
  return (
    <li className="flex flex-col gap-2 rounded-md border border-default bg-surface p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm font-medium text-primary">
            {entry.title ?? kindLabel(entry.kind)}
          </span>
          <Badge variant="default" size="sm">
            {kindLabel(entry.kind)}
          </Badge>
          <Badge variant={badge.variant} size="sm">
            {badge.label}
          </Badge>
          {score !== undefined ? (
            <span className="text-xs text-tertiary">{Math.round(score * 100)}%</span>
          ) : null}
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => {
            onRequestDelete(entry.id);
          }}
        >
          {t("memory.entry.deleteAction")}
        </Button>
      </div>
      <p className="whitespace-pre-wrap text-sm text-secondary">{entry.content}</p>
      <span className="text-xs text-tertiary">{formatDateTime(entry.created_at)}</span>
    </li>
  );
}

export interface MemoryEntryListProps {
  items: MemoryListItem[];
  onDelete: (entryId: string) => void;
  deletePending: boolean;
  "aria-label": string;
}

/** List + delete-confirmation dialog. */
export function MemoryEntryList({ items, onDelete, deletePending, ...aria }: MemoryEntryListProps) {
  const [pendingId, setPendingId] = useState<string | null>(null);

  return (
    <>
      <ul aria-label={aria["aria-label"]} className="flex flex-col gap-3">
        {items.map((item) => (
          <MemoryEntryRow
            key={item.entry.id}
            entry={item.entry}
            {...(item.score !== undefined ? { score: item.score } : {})}
            onRequestDelete={setPendingId}
          />
        ))}
      </ul>

      <Dialog
        open={pendingId !== null}
        onOpenChange={(open) => {
          if (!open) setPendingId(null);
        }}
      >
        <Dialog.Content size="sm">
          <Dialog.Header>
            <Dialog.Title>{t("memory.entry.deleteConfirm.title")}</Dialog.Title>
            <Dialog.Description>{t("memory.entry.deleteConfirm.description")}</Dialog.Description>
          </Dialog.Header>
          <Dialog.Footer>
            <Button
              variant="secondary"
              onClick={() => {
                setPendingId(null);
              }}
            >
              {t("common.cancel")}
            </Button>
            <Button
              variant="destructive"
              loading={deletePending}
              onClick={() => {
                if (pendingId !== null) onDelete(pendingId);
                setPendingId(null);
              }}
            >
              {t("memory.entry.deleteAction")}
            </Button>
          </Dialog.Footer>
        </Dialog.Content>
      </Dialog>
    </>
  );
}
