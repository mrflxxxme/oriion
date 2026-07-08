/**
 * agents endpoints — read-only slice pinned to the live backend
 * (backend/src/agents/routers/instances.py + schemas.py).
 *
 * Only `listForCell` is consumed today: the memory feature needs real
 * `agent_id`s to scope the role-memory picker (component-inventory.md
 * Select), and this cell-scoped list is the only live source for them.
 */
import { z } from "zod";
import { apiFetch } from "./client";

export const agentInstanceSchema = z.object({
  id: z.string(),
  cell_id: z.string(),
  agent_archetype_id: z.string(),
  custom_name: z.string().nullable().optional(),
  total_tasks_completed: z.number().optional(),
  last_used_at: z.string().nullable().optional(),
  created_at: z.string().optional(),
  archived_at: z.string().nullable().optional(),
});
export type AgentInstance = z.infer<typeof agentInstanceSchema>;

export const agentsApi = {
  listForCell: (cellId: string) =>
    apiFetch(`/cells/${cellId}/agents`, { schema: z.array(agentInstanceSchema) }),
};
