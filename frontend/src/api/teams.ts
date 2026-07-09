/**
 * teams endpoint — provision a team-preset into a cell
 * (POST /cells/{cell_id}/teams — backend/src/agents/routers/teams.py).
 * Schema pinned to `TeamProvisionResponse` (backend/src/agents/schemas.py);
 * reuses `agentInstanceSchema` from api/agents.ts for the nested instances.
 */
import { z } from "zod";
import { apiFetch } from "./client";
import { agentInstanceSchema } from "./agents";

export const teamProvisionResponseSchema = z.object({
  team_preset_id: z.string(),
  cell_id: z.string(),
  agent_instances: z.array(agentInstanceSchema),
});
export type TeamProvisionResponse = z.infer<typeof teamProvisionResponseSchema>;

export interface TeamProvisionPayload {
  /** team_preset.slug to provision — see agents/seed_data/*_v1.py PRESET_SLUG. */
  preset_key: string;
}

export const teamsApi = {
  provision: (cellId: string, payload: TeamProvisionPayload) =>
    apiFetch(`/cells/${cellId}/teams`, {
      method: "POST",
      body: payload,
      schema: teamProvisionResponseSchema,
    }),
};
