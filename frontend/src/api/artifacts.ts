/**
 * artifacts read endpoint — schema pinned to the live backend
 * (backend/src/artifacts/routers/artifacts.py, ADR-038). Cell scope comes
 * from the RLS tenant context (`get_current_cell_id`) — no path param
 * (mirrors memory/billing). Only the list envelope is consumed here (the
 * Dashboard's artifacts summary); versions/Yjs/uploads belong to a future
 * artifacts-editing feature.
 *
 * Note: this is the generic document/asset envelope (title + type + owner),
 * distinct from the inline `matrix`/`analysis`/`brief` task-output artifacts
 * surfaced on TaskResultPage (api/tasks.ts's `Artifact` — those live only in
 * a task's CoordinatorOutput/SSE ledger, not this envelope table).
 */
import { z } from "zod";
import { apiFetch } from "./client";

export const artifactEnvelopeSchema = z.object({
  id: z.string(),
  cell_id: z.string(),
  artifact_type: z.string(),
  title: z.string(),
  tags: z.array(z.string()),
  owner_user_id: z.string().nullable(),
  created_by_agent_id: z.string().nullable(),
  current_version_num: z.number(),
  created_at: z.string(),
  updated_at: z.string(),
});
export type ArtifactEnvelope = z.infer<typeof artifactEnvelopeSchema>;

export interface ListArtifactsParams {
  limit?: number;
}

export const artifactsApi = {
  list: (params: ListArtifactsParams = {}) => {
    const query = new URLSearchParams();
    if (params.limit !== undefined) query.set("limit", String(params.limit));
    const qs = query.toString();
    return apiFetch(`/artifacts${qs ? `?${qs}` : ""}`, {
      schema: z.array(artifactEnvelopeSchema),
    });
  },
};
