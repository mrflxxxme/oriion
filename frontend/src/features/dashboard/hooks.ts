/**
 * Dashboard data hooks (TanStack Query) — a read-only summary surface over
 * ready APIs: recent tasks (locally-tracked ids + the existing per-task GET;
 * see store.ts for why there's no list-tasks query), the artifacts envelope
 * list, and the billing balance. Each is an independent query so the page can
 * render per-section loading/empty/error states.
 */
import { useQueries, useQuery, type UseQueryResult } from "@tanstack/react-query";
import { tasksApi, type Task } from "@/api/tasks";
import { artifactsApi, type ArtifactEnvelope } from "@/api/artifacts";
import { billingApi, type Balance } from "@/api/billing";
import { useCellsList } from "@/features/cells/hooks";
import { useRecentTasksStore, type RecentTaskRef } from "./store";

const RECENT_ARTIFACTS_LIMIT = 5;

/** The Wave-0 "current" cell id — mirrors memory/hooks.ts's useCurrentCellId. */
export function useCurrentCellId(): string | undefined {
  const { data: cells } = useCellsList();
  return cells?.[0]?.id;
}

export function useRecentTaskRefs(): RecentTaskRef[] {
  return useRecentTasksStore((s) => s.recentTasks);
}

export interface RecentTaskSummary {
  ref: RecentTaskRef;
  task: Task | undefined;
  isLoading: boolean;
  isError: boolean;
}

/** One `useTask`-equivalent query per tracked id, folded into a single array. */
export function useRecentTaskSummaries(refs: RecentTaskRef[]): RecentTaskSummary[] {
  const results: UseQueryResult<Task>[] = useQueries({
    queries: refs.map((ref) => ({
      queryKey: ["cells", ref.cellId, "tasks", ref.taskId],
      queryFn: () => tasksApi.get(ref.cellId, ref.taskId),
    })),
  });

  return refs.map((ref, index) => {
    const result = results[index];
    return {
      ref,
      task: result?.data,
      isLoading: result?.isLoading ?? false,
      isError: result?.isError ?? false,
    };
  });
}

export function useRecentArtifacts(): UseQueryResult<ArtifactEnvelope[]> {
  return useQuery({
    queryKey: ["dashboard", "artifacts"],
    queryFn: () => artifactsApi.list({ limit: RECENT_ARTIFACTS_LIMIT }),
  });
}

export function useBalance(): UseQueryResult<Balance> {
  return useQuery({
    queryKey: ["dashboard", "balance"],
    queryFn: () => billingApi.getBalance(),
  });
}
