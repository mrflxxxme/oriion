/**
 * Memory feature data hooks (TanStack Query).
 *
 * Cell memory is scoped implicitly by the backend's RLS tenant context
 * (Wave-0 single-cell) — no `cellId` argument needed. Role memory needs a
 * concrete `agent_id`; `useCellAgents` sources real instances from the
 * cell-scoped agents endpoint (`GET /cells/{cell_id}/agents`), reusing the
 * cells feature's `useCellsList` to resolve "the" Wave-0 cell id — the same
 * data the Cells feature already surfaces, just fed into a different query.
 */
import { useMutation, useQuery, useQueryClient, type UseQueryResult } from "@tanstack/react-query";
import {
  memoryApi,
  type AddMemoryPayload,
  type AddRoleMemoryPayload,
  type MemoryEntry,
  type MemorySearchHit,
  type RoleMemoryEntry,
  type RoleMemorySearchHit,
} from "@/api/memory";
import { agentsApi, type AgentInstance } from "@/api/agents";
import { ApiException } from "@/api/client";
import { toast } from "@/components/ui";
import { useCellsList } from "@/features/cells/hooks";

const LIST_LIMIT = 100;

const cellMemoryKey = ["memory", "cell"] as const;
const roleMemoryKey = (agentId: string) => ["memory", "role", agentId] as const;

function reportError(error: ApiException): void {
  toast.error(error.error.message);
}

// ── cell memory ────────────────────────────────────────────────────────── //

export function useCellMemoryList(): UseQueryResult<MemoryEntry[]> {
  return useQuery({
    queryKey: cellMemoryKey,
    queryFn: () => memoryApi.list({ limit: LIST_LIMIT }),
  });
}

export function useCellMemorySearch(query: string): UseQueryResult<MemorySearchHit[]> {
  const trimmed = query.trim();
  return useQuery({
    queryKey: [...cellMemoryKey, "search", trimmed],
    queryFn: () => memoryApi.search(trimmed),
    enabled: trimmed.length > 0,
  });
}

export function useAddCellMemory() {
  const queryClient = useQueryClient();
  return useMutation<MemoryEntry, ApiException, AddMemoryPayload>({
    mutationFn: (payload) => memoryApi.add(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: cellMemoryKey });
    },
    onError: reportError,
  });
}

export function useDeleteCellMemory() {
  const queryClient = useQueryClient();
  return useMutation<undefined, ApiException, string>({
    mutationFn: (entryId) => memoryApi.remove(entryId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: cellMemoryKey });
    },
    onError: reportError,
  });
}

// ── agents (for the role-memory picker) ───────────────────────────────── //

/** The Wave-0 "current" cell id — first cell across the user's workspaces. */
export function useCurrentCellId(): string | undefined {
  const { data: cells } = useCellsList();
  return cells?.[0]?.id;
}

export function useCellAgents(cellId: string | undefined): UseQueryResult<AgentInstance[]> {
  return useQuery({
    queryKey: ["memory", "agents", cellId],
    queryFn: () => agentsApi.listForCell(cellId as string),
    enabled: cellId !== undefined,
  });
}

// ── role memory (per agent instance) ──────────────────────────────────── //

export function useRoleMemoryList(agentId: string | undefined): UseQueryResult<RoleMemoryEntry[]> {
  return useQuery({
    queryKey: roleMemoryKey(agentId ?? "none"),
    queryFn: () => memoryApi.listForAgent(agentId as string, { limit: LIST_LIMIT }),
    enabled: agentId !== undefined,
  });
}

export function useRoleMemorySearch(
  agentId: string | undefined,
  query: string,
): UseQueryResult<RoleMemorySearchHit[]> {
  const trimmed = query.trim();
  return useQuery({
    queryKey: [...roleMemoryKey(agentId ?? "none"), "search", trimmed],
    queryFn: () => memoryApi.searchForAgent(agentId as string, trimmed),
    enabled: agentId !== undefined && trimmed.length > 0,
  });
}

export function useAddRoleMemory(agentId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation<RoleMemoryEntry, ApiException, AddRoleMemoryPayload>({
    mutationFn: (payload) => memoryApi.addForAgent(agentId as string, payload),
    onSuccess: () => {
      if (agentId !== undefined) {
        void queryClient.invalidateQueries({ queryKey: roleMemoryKey(agentId) });
      }
    },
    onError: reportError,
  });
}

export function useDeleteRoleMemory(agentId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation<undefined, ApiException, string>({
    mutationFn: (entryId) => memoryApi.removeForAgent(agentId as string, entryId),
    onSuccess: () => {
      if (agentId !== undefined) {
        void queryClient.invalidateQueries({ queryKey: roleMemoryKey(agentId) });
      }
    },
    onError: reportError,
  });
}
