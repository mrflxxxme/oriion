/**
 * Task-feature data hooks (C10).
 *
 * `useCreateAndRunTask` owns the non-blocking three-step submit flow:
 *   1. POST /tasks            → task (status "queued")   [awaited]
 *   2. navigate to result     → /cells/$cellId/tasks/$id [immediate]
 *   3. POST /tasks/$id/run     → fire-and-forget (~90s)  [NOT awaited]
 *
 * Step 3 must never be awaited in the UI flow: the result page (C11/C12) owns
 * progress via SSE + polling, so awaiting `run()` here would freeze the form
 * for the full ~90s orchestration. We deliberately `void` the promise.
 *
 * This file is additive: C11/C12 may append `useTask` / `useTaskStream` here.
 */
import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { tasksApi, type Task } from "@/api/tasks";
import { ApiException } from "@/api/client";
import { toast } from "@/components/ui";

/** Default title when the prompt is long — backend requires a non-empty title. */
const DEFAULT_TITLE = "Задача";
/** Title is a short slice of the prompt for at-a-glance lists. */
const TITLE_MAX = 60;

function deriveTitle(prompt: string): string {
  const trimmed = prompt.trim();
  if (trimmed.length === 0) return DEFAULT_TITLE;
  return trimmed.length > TITLE_MAX ? `${trimmed.slice(0, TITLE_MAX)}…` : trimmed;
}

export interface UseCreateAndRunTask {
  /** Submit handler — creates the task, navigates, then fires run() unawaited. */
  submit: (prompt: string) => void;
  /** True while the create request is in flight (blocks the submit button). */
  isPending: boolean;
}

/**
 * Create-and-run mutation bound to a cell. Returns a `submit(prompt)` callback
 * plus the in-flight flag for the create step.
 */
export function useCreateAndRunTask(cellId: string): UseCreateAndRunTask {
  const navigate = useNavigate();

  const mutation = useMutation<Task, ApiException, string>({
    mutationFn: (prompt: string) =>
      tasksApi.create(cellId, { title: deriveTitle(prompt), prompt }),
    onSuccess: (task) => {
      // Fire the blocking orchestration WITHOUT awaiting — the result page
      // owns progress. Swallow async rejection so it never bubbles unhandled.
      void tasksApi.run(cellId, task.id).catch(() => {
        // Run failures surface on the result page (SSE/poll); nothing to do here.
      });
      void navigate({
        to: "/cells/$cellId/tasks/$taskId",
        params: { cellId, taskId: task.id },
      });
    },
    onError: (error: ApiException) => {
      toast.error(error.error.message);
    },
  });

  return {
    submit: (prompt: string) => {
      mutation.mutate(prompt);
    },
    isPending: mutation.isPending,
  };
}
