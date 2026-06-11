/**
 * multitenancy endpoints — schemas pinned to the live backend.
 * There is NO flat GET /cells: list = GET /workspaces -> per-ws GET cells.
 */
import { z } from "zod";
import { apiFetch } from "./client";

export const workspaceSchema = z.object({
  id: z.string(),
  slug: z.string().optional(),
  display_name: z.string(),
  plan_tier: z.string().optional(),
  created_at: z.string().optional(),
});
export type Workspace = z.infer<typeof workspaceSchema>;

export const workspacePageSchema = z.object({
  items: z.array(workspaceSchema),
  next_cursor: z.string().nullable().optional(),
});

export const cellSchema = z.object({
  id: z.string(),
  workspace_id: z.string(),
  slug: z.string(),
  display_name: z.string(),
  vertical_template_slug: z.string().nullable().optional(),
  settings: z.record(z.string(), z.unknown()).optional(),
  created_at: z.string().optional(),
  updated_at: z.string().optional(),
  archived_at: z.string().nullable().optional(),
});
export type Cell = z.infer<typeof cellSchema>;

export const cellPageSchema = z.object({
  items: z.array(cellSchema),
  next_cursor: z.string().nullable().optional(),
});

export const cellsApi = {
  listWorkspaces: () => apiFetch("/workspaces", { schema: workspacePageSchema }),

  listCells: (workspaceId: string) =>
    apiFetch(`/workspaces/${workspaceId}/cells`, { schema: cellPageSchema }),

  getCell: (cellId: string) => apiFetch(`/cells/${cellId}`, { schema: cellSchema }),

  /** Convenience: fan out over all workspaces and flatten their cells. */
  async listAllCells(): Promise<Cell[]> {
    const { items: workspaces } = await this.listWorkspaces();
    const pages = await Promise.all(workspaces.map((w) => this.listCells(w.id)));
    return pages.flatMap((p) => p.items);
  },
};
