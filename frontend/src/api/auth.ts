/**
 * iam endpoints — schemas pinned to the live backend (frontend/docs/api-notes.md).
 */
import { z } from "zod";
import { apiFetch } from "./client";

export const tokenPairSchema = z.object({
  access_token: z.string(),
  refresh_token: z.string(),
  expires_in: z.number(),
  token_type: z.string(),
});
export type TokenPair = z.infer<typeof tokenPairSchema>;

export const registerResponseSchema = z.object({
  user_id: z.string(),
  workspace_id: z.string(),
  cell_id: z.string(),
  email: z.string(),
  email_verification_sent: z.boolean().optional(),
});
export type RegisterResponse = z.infer<typeof registerResponseSchema>;

export const userSchema = z.object({
  id: z.string(),
  email: z.string(),
  email_verified_at: z.string().nullable().optional(),
  display_name: z.string().nullable().optional(),
  locale: z.string().optional(),
  timezone: z.string().optional(),
  created_at: z.string().optional(),
  updated_at: z.string().optional(),
});
export type User = z.infer<typeof userSchema>;

export interface RegisterPayload {
  email: string;
  password: string;
  display_name?: string;
  locale?: string;
  consent_pdn: boolean;
  consent_marketing?: boolean;
}

export const authApi = {
  register: (payload: RegisterPayload) =>
    apiFetch("/auth/register", {
      method: "POST",
      body: payload,
      schema: registerResponseSchema,
      authRequired: false,
    }),

  login: (email: string, password: string) =>
    apiFetch("/auth/login", {
      method: "POST",
      body: { email, password },
      schema: tokenPairSchema,
      authRequired: false,
    }),

  logout: (refreshToken: string) =>
    apiFetch<undefined>("/auth/logout", {
      method: "POST",
      body: { refresh_token: refreshToken },
    }),

  me: () => apiFetch("/users/me", { schema: userSchema }),
};
