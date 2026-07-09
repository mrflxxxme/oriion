/**
 * billing read endpoints — schemas pinned to the live backend
 * (backend/src/billing/routers/billing.py, backend/src/billing/schemas.py).
 *
 * Cell scope comes from the RLS tenant context (`get_current_cell_id`) — not
 * a path/query param (Wave-0 single-cell, mirrors memory/artifacts). Only
 * `/balance` is consumed today (Dashboard credit-balance summary); plans /
 * subscription / transactions are out of scope for 01.12.
 */
import { z } from "zod";
import { apiFetch } from "./client";

export const balanceSchema = z.object({
  cell_id: z.string(),
  balance_credits: z.string(),
  period_usage_credits: z.string(),
  period_start: z.string().nullable().optional(),
  period_end: z.string().nullable().optional(),
  soft_cap_credits: z.string().nullable().optional(),
  hard_cap_credits: z.string().nullable().optional(),
  daily_usage_credits: z.string(),
  per_day_cap_credits: z.string().nullable().optional(),
});
export type Balance = z.infer<typeof balanceSchema>;

export const billingApi = {
  getBalance: () => apiFetch("/billing/balance", { schema: balanceSchema }),
};
