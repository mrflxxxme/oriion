/**
 * tasks endpoints — schemas pinned to the live backend (api-notes.md).
 * Three-step flow: POST /tasks (queued) -> POST /run (blocking) -> GET /stream.
 */
import { z } from "zod";
import { apiFetch } from "./client";

export const taskSchema = z.object({
  id: z.string(),
  cell_id: z.string(),
  parent_task_id: z.string().nullable().optional(),
  initiated_by_user_id: z.string().optional(),
  title: z.string(),
  description: z.string().optional(),
  status: z.string(),
  priority: z.number().optional(),
  started_at: z.string().nullable().optional(),
  completed_at: z.string().nullable().optional(),
  total_cost_credits: z.string().optional(),
  total_input_tokens: z.number().optional(),
  total_output_tokens: z.number().optional(),
  created_at: z.string().optional(),
});
export type Task = z.infer<typeof taskSchema>;

/** CoordinatorOutput artifact — inline markdown (matrix/analysis/brief). */
export const artifactSchema = z.object({
  id: z.string().optional(),
  type: z.string(),
  path_or_inline: z.string(),
});
export type Artifact = z.infer<typeof artifactSchema>;

export const coordinatorOutputSchema = z.object({
  summary: z.string().optional(),
  delegation_plan: z.array(z.unknown()).optional(),
  citations: z.array(z.unknown()).optional(),
  artifacts: z.array(artifactSchema).default([]),
  total_cost_credits: z.union([z.string(), z.number()]).optional(),
});
export type CoordinatorOutput = z.infer<typeof coordinatorOutputSchema>;

export const runResultSchema = z.object({
  task_id: z.string().optional(),
  status: z.string(),
  result: coordinatorOutputSchema.optional(),
});
export type RunResult = z.infer<typeof runResultSchema>;

export interface CreateTaskPayload {
  title: string;
  prompt: string;
  description?: string;
}

export const tasksApi = {
  create: (cellId: string, payload: CreateTaskPayload) =>
    apiFetch(`/cells/${cellId}/tasks`, { method: "POST", body: payload, schema: taskSchema }),

  /** Blocking dispatch — runs the orchestration (~90s) and returns the result. */
  run: (cellId: string, taskId: string, signal?: AbortSignal) =>
    apiFetch(`/cells/${cellId}/tasks/${taskId}/run`, {
      method: "POST",
      schema: runResultSchema,
      ...(signal ? { signal } : {}),
    }),

  get: (cellId: string, taskId: string) =>
    apiFetch(`/cells/${cellId}/tasks/${taskId}`, { schema: taskSchema }),

  cancel: (cellId: string, taskId: string) =>
    apiFetch<unknown>(`/cells/${cellId}/tasks/${taskId}/cancel`, { method: "POST" }),
};

/** Path of the SSE stream endpoint (consumed by api/sse.ts with a Bearer header). */
export function taskStreamPath(cellId: string, taskId: string): string {
  return `/api/v1/cells/${cellId}/tasks/${taskId}/stream`;
}
