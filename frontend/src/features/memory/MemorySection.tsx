/**
 * MemorySectionView — presentational "one memory scope" surface: search box,
 * collapsible add form, and the three query states (loading / error / empty)
 * around the entry list. Shared by the cell- and role-memory tabs in
 * `MemoryPanelPage`; each tab owns its own TanStack Query hooks and passes
 * already-resolved data in, so this component has no data-fetching of its own.
 */
import { useId, useState } from "react";
import type { SelectOption } from "@/components/ui";
import { Button, EmptyState, Input, Skeleton } from "@/components/ui";
import { t } from "@/lib/i18n";
import { MemoryAddForm, type MemoryAddPayload } from "./MemoryAddForm";
import { MemoryEntryList, type MemoryListItem } from "./MemoryEntryList";

export interface MemorySectionViewProps {
  items: MemoryListItem[];
  isLoading: boolean;
  isError: boolean;
  onRetry: () => void;
  emptyTitle: string;
  emptyDescription: string;
  kindOptions: SelectOption[];
  defaultKind: string;
  onAdd: (payload: MemoryAddPayload) => void;
  addPending: boolean;
  onDelete: (entryId: string) => void;
  deletePending: boolean;
  searchValue: string;
  onSearchValueChange: (value: string) => void;
  isSearchActive: boolean;
  isSearching: boolean;
  listAriaLabel: string;
}

export function MemorySectionView({
  items,
  isLoading,
  isError,
  onRetry,
  emptyTitle,
  emptyDescription,
  kindOptions,
  defaultKind,
  onAdd,
  addPending,
  onDelete,
  deletePending,
  searchValue,
  onSearchValueChange,
  isSearchActive,
  isSearching,
  listAriaLabel,
}: MemorySectionViewProps) {
  const [addOpen, setAddOpen] = useState(false);
  const searchId = useId();

  const showListLoading = isSearchActive ? isSearching : isLoading;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end gap-2">
        <div className="flex flex-1 flex-col gap-1.5">
          <label htmlFor={searchId} className="text-sm font-medium text-primary">
            {t("memory.search.label")}
          </label>
          <Input
            id={searchId}
            type="search"
            placeholder={t("memory.search.placeholder")}
            value={searchValue}
            onChange={(e) => {
              onSearchValueChange(e.target.value);
            }}
          />
        </div>
        {isSearchActive ? (
          <Button
            type="button"
            variant="secondary"
            onClick={() => {
              onSearchValueChange("");
            }}
          >
            {t("memory.search.clear")}
          </Button>
        ) : null}
        <Button
          type="button"
          variant={addOpen ? "secondary" : "primary"}
          onClick={() => {
            setAddOpen((open) => !open);
          }}
        >
          {t("memory.add.toggle")}
        </Button>
      </div>

      {addOpen ? (
        <MemoryAddForm
          kindOptions={kindOptions}
          defaultKind={defaultKind}
          onSubmit={onAdd}
          isPending={addPending}
        />
      ) : null}

      {isError ? (
        <EmptyState
          variant="danger"
          title={t("memory.error.list")}
          action={{ label: t("common.retry"), onClick: onRetry }}
        />
      ) : showListLoading ? (
        <div aria-busy="true" className="flex flex-col gap-3">
          <Skeleton height={72} />
          <Skeleton height={72} />
        </div>
      ) : items.length === 0 ? (
        <EmptyState
          title={isSearchActive ? t("memory.search.empty.title") : emptyTitle}
          {...(isSearchActive ? {} : { description: emptyDescription })}
        />
      ) : (
        <MemoryEntryList
          items={items}
          onDelete={onDelete}
          deletePending={deletePending}
          aria-label={listAriaLabel}
        />
      )}
    </div>
  );
}
