/**
 * Onboarding wizard data hooks (Phase 01.12).
 *
 * Two write flows, both bound to the user's Wave-0 cell:
 *  - `useProvisionPreset`  → POST /cells/{cellId}/teams (`preset_key`), i.e.
 *    teamsApi.provision. Idempotent server-side, so re-running (e.g. the user
 *    steps back and re-picks) is safe.
 *  - `useSeedFirstTask`    → tasksApi.create then tasksApi.run (fire-and-forget,
 *    mirrors tasks/hooks.ts's `useCreateAndRunTask`), records the task in the
 *    dashboard's recent-tasks store, then navigates to the live task-result
 *    page so the user watches progress.
 */
import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { teamsApi, type TeamProvisionResponse } from "@/api/teams";
import { tasksApi, type Task } from "@/api/tasks";
import { ApiException } from "@/api/client";
import { toast } from "@/components/ui";
import { useCellsList } from "@/features/cells/hooks";
import { useRecentTasksStore } from "@/features/dashboard/store";
import type { PresetKey } from "./presets";

/** The Wave-0 "current" cell id — first cell across the user's workspaces. */
export function useCurrentCellId(): string | undefined {
  const { data: cells } = useCellsList();
  return cells?.[0]?.id;
}

export function useCellsStatus(): { isLoading: boolean; isError: boolean; hasCell: boolean } {
  const { data: cells, isLoading, isError } = useCellsList();
  return { isLoading, isError, hasCell: (cells?.length ?? 0) > 0 };
}

export function useProvisionPreset(cellId: string | undefined) {
  return useMutation<TeamProvisionResponse, ApiException, PresetKey>({
    mutationFn: (presetKey) => teamsApi.provision(cellId as string, { preset_key: presetKey }),
    onError: (error) => {
      toast.error(error.error.message);
    },
  });
}

const TITLE_MAX = 60;

function deriveTitle(fallback: string, prompt: string): string {
  const trimmed = prompt.trim();
  if (trimmed.length === 0) return fallback;
  return trimmed.length > TITLE_MAX ? `${trimmed.slice(0, TITLE_MAX)}…` : trimmed;
}

export interface SeedFirstTaskInput {
  title: string;
  prompt: string;
}

/**
 * Create + run the first task, record it for the dashboard, then navigate to
 * the task-result page. `run()` is fired unawaited (the result page owns
 * progress via SSE/poll — awaiting it would freeze the wizard ~90s).
 */
export function useSeedFirstTask(cellId: string | undefined) {
  const navigate = useNavigate();
  const addRecentTask = useRecentTasksStore((s) => s.addRecentTask);

  const mutation = useMutation<Task, ApiException, SeedFirstTaskInput>({
    mutationFn: ({ title, prompt }) =>
      tasksApi.create(cellId as string, { title: deriveTitle(title, prompt), prompt }),
    onSuccess: (task) => {
      const resolvedCellId = cellId as string;
      void tasksApi.run(resolvedCellId, task.id).catch(() => {
        // Run failures surface on the result page (SSE/poll); nothing to do here.
      });
      addRecentTask({
        cellId: resolvedCellId,
        taskId: task.id,
        title: task.title,
        createdAt: task.created_at ?? new Date().toISOString(),
      });
      void navigate({
        to: "/cells/$cellId/tasks/$taskId",
        params: { cellId: resolvedCellId, taskId: task.id },
      });
    },
    onError: (error) => {
      toast.error(error.error.message);
    },
  });

  return {
    submit: (input: SeedFirstTaskInput) => {
      mutation.mutate(input);
    },
    isPending: mutation.isPending,
  };
}
