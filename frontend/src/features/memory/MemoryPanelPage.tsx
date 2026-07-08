/**
 * MemoryPanelPage — «Что помнит команда/агент» (Phase 01.4-ui).
 *
 * Two tabs over the live `/api/v1/memory/*` API:
 *  - Ячейка: shared cell memory (no `cell_id` needed — RLS tenant-context
 *    scoped, Wave-0 single-cell).
 *  - Агент: per agent-instance role memory, agent chosen from the cell's
 *    live agent instances (`GET /cells/{cell_id}/agents` — the same source
 *    the rest of the app would use once it lists agents; today only this
 *    picker consumes it).
 *
 * "Edit" is delete + prefill-add (no PATCH endpoint) — see `MemoryAddForm`.
 */
import { useEffect, useMemo, useState } from "react";
import type { SelectOption } from "@/components/ui";
import { Breadcrumb, EmptyState, Select, Skeleton, Tabs } from "@/components/ui";
import { t } from "@/lib/i18n";
import { CELL_MEMORY_KINDS, ROLE_MEMORY_KINDS, type CellMemoryKind } from "@/api/memory";
import { kindLabel } from "./labels";
import type { MemoryListItem } from "./MemoryEntryList";
import { MemorySectionView } from "./MemorySection";
import type { MemoryAddPayload } from "./MemoryAddForm";
import {
  useAddCellMemory,
  useAddRoleMemory,
  useCellAgents,
  useCellMemoryList,
  useCellMemorySearch,
  useCurrentCellId,
  useDeleteCellMemory,
  useDeleteRoleMemory,
  useRoleMemoryList,
  useRoleMemorySearch,
} from "./hooks";

const CELL_KIND_OPTIONS: SelectOption[] = CELL_MEMORY_KINDS.map((kind) => ({
  value: kind,
  label: kindLabel(kind),
}));

const ROLE_KIND_OPTIONS: SelectOption[] = ROLE_MEMORY_KINDS.map((kind) => ({
  value: kind,
  label: kindLabel(kind),
}));

function CellMemoryTab() {
  const [searchValue, setSearchValue] = useState("");
  const isSearchActive = searchValue.trim().length > 0;

  const listQuery = useCellMemoryList();
  const searchQuery = useCellMemorySearch(searchValue);
  const addMutation = useAddCellMemory();
  const deleteMutation = useDeleteCellMemory();

  const items: MemoryListItem[] = isSearchActive
    ? (searchQuery.data ?? []).map((hit) => ({ entry: hit.entry, score: hit.score }))
    : (listQuery.data ?? []).map((entry) => ({ entry }));

  return (
    <MemorySectionView
      items={items}
      isLoading={listQuery.isLoading}
      isError={isSearchActive ? searchQuery.isError : listQuery.isError}
      onRetry={() => {
        if (isSearchActive) void searchQuery.refetch();
        else void listQuery.refetch();
      }}
      emptyTitle={t("memory.empty.cell.title")}
      emptyDescription={t("memory.empty.cell.description")}
      kindOptions={CELL_KIND_OPTIONS}
      defaultKind={CELL_MEMORY_KINDS[0]}
      onAdd={(payload: MemoryAddPayload) => {
        addMutation.mutate({
          kind: payload.kind as CellMemoryKind,
          content: payload.content,
          contains_pii: payload.contains_pii,
          ...(payload.title !== undefined ? { title: payload.title } : {}),
        });
      }}
      addPending={addMutation.isPending}
      onDelete={(entryId) => {
        deleteMutation.mutate(entryId);
      }}
      deletePending={deleteMutation.isPending}
      searchValue={searchValue}
      onSearchValueChange={setSearchValue}
      isSearchActive={isSearchActive}
      isSearching={searchQuery.isFetching}
      listAriaLabel={t("memory.tab.cell")}
    />
  );
}

function RoleMemoryTab() {
  const cellId = useCurrentCellId();
  const agentsQuery = useCellAgents(cellId);
  const agents = useMemo(() => agentsQuery.data ?? [], [agentsQuery.data]);
  const [selectedAgentId, setSelectedAgentId] = useState<string | undefined>(undefined);

  useEffect(() => {
    if (selectedAgentId === undefined && agents.length > 0) {
      setSelectedAgentId(agents[0]?.id);
    }
  }, [agents, selectedAgentId]);

  const [searchValue, setSearchValue] = useState("");
  const isSearchActive = searchValue.trim().length > 0;

  const listQuery = useRoleMemoryList(selectedAgentId);
  const searchQuery = useRoleMemorySearch(selectedAgentId, searchValue);
  const addMutation = useAddRoleMemory(selectedAgentId);
  const deleteMutation = useDeleteRoleMemory(selectedAgentId);

  const items: MemoryListItem[] = isSearchActive
    ? (searchQuery.data ?? []).map((hit) => ({ entry: hit.entry, score: hit.score }))
    : (listQuery.data ?? []).map((entry) => ({ entry }));

  const agentOptions: SelectOption[] = agents.map((agent) => ({
    value: agent.id,
    label: agent.custom_name ?? `${t("memory.role.agentFallbackPrefix")} ${agent.id.slice(0, 8)}`,
  }));

  if (agentsQuery.isLoading) {
    return (
      <div aria-busy="true" className="flex flex-col gap-3">
        <Skeleton height={40} width="40%" />
        <Skeleton height={72} />
      </div>
    );
  }

  if (agentsQuery.isError) {
    return (
      <EmptyState
        variant="danger"
        title={t("memory.role.error.agents")}
        action={{
          label: t("common.retry"),
          onClick: () => {
            void agentsQuery.refetch();
          },
        }}
      />
    );
  }

  if (agents.length === 0) {
    return (
      <EmptyState
        title={t("memory.role.noAgents.title")}
        description={t("memory.role.noAgents.description")}
      />
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex max-w-xs flex-col gap-1.5">
        <label htmlFor="memory-role-agent" className="text-sm font-medium text-primary">
          {t("memory.role.agentLabel")}
        </label>
        <Select
          id="memory-role-agent"
          options={agentOptions}
          placeholder={t("memory.role.agentPlaceholder")}
          // Always controlled (never omit `value`) — `agents[0]` resolves
          // asynchronously and flipping uncontrolled -> controlled once it
          // lands would trip React's controlled-input warning.
          value={selectedAgentId ?? ""}
          onValueChange={setSelectedAgentId}
        />
      </div>

      <MemorySectionView
        items={items}
        isLoading={listQuery.isLoading}
        isError={isSearchActive ? searchQuery.isError : listQuery.isError}
        onRetry={() => {
          if (isSearchActive) void searchQuery.refetch();
          else void listQuery.refetch();
        }}
        emptyTitle={t("memory.empty.role.title")}
        emptyDescription={t("memory.empty.role.description")}
        kindOptions={ROLE_KIND_OPTIONS}
        defaultKind={ROLE_MEMORY_KINDS[0]}
        onAdd={(payload: MemoryAddPayload) => {
          addMutation.mutate({
            kind: payload.kind as (typeof ROLE_MEMORY_KINDS)[number],
            content: payload.content,
            contains_pii: payload.contains_pii,
            ...(payload.title !== undefined ? { title: payload.title } : {}),
          });
        }}
        addPending={addMutation.isPending}
        onDelete={(entryId) => {
          deleteMutation.mutate(entryId);
        }}
        deletePending={deleteMutation.isPending}
        searchValue={searchValue}
        onSearchValueChange={setSearchValue}
        isSearchActive={isSearchActive}
        isSearching={searchQuery.isFetching}
        listAriaLabel={t("memory.tab.role")}
      />
    </div>
  );
}

export function MemoryPanelPage() {
  return (
    <div className="flex flex-col gap-6">
      <Breadcrumb items={[{ label: t("memory.crumb") }]} />
      <h1 className="text-3xl font-bold text-primary">{t("memory.title")}</h1>

      <Tabs defaultValue="cell">
        <Tabs.List>
          <Tabs.Trigger value="cell">{t("memory.tab.cell")}</Tabs.Trigger>
          <Tabs.Trigger value="role">{t("memory.tab.role")}</Tabs.Trigger>
        </Tabs.List>
        <Tabs.Content value="cell">
          <CellMemoryTab />
        </Tabs.Content>
        <Tabs.Content value="role">
          <RoleMemoryTab />
        </Tabs.Content>
      </Tabs>
    </div>
  );
}
