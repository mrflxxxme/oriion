/**
 * Auth form schemas (zod) — single source of truth for client-side validation.
 *
 * Messages are ru-RU via t() so field errors match the rest of the UI copy.
 * AC12 (ФЗ-152): registration requires an explicit consent_pdn === true.
 */
import { z } from "zod";
import { t } from "@/lib/i18n";

export const loginSchema = z.object({
  email: z.email(t("auth.error.emailInvalid")),
  password: z.string().min(1, t("auth.error.passwordRequired")),
  remember: z.boolean().optional(),
});

export type LoginValues = z.infer<typeof loginSchema>;

export const registerSchema = z
  .object({
    email: z.email(t("auth.error.emailInvalid")),
    password: z.string().min(12, t("auth.error.passwordTooShort")),
    passwordConfirm: z.string(),
    displayName: z.string().optional(),
    // AC12 — ФЗ-152: consent must be explicitly accepted. Typed as boolean
    // (friendlier with rhf/Checkbox) but refined to reject `false`.
    consentPdn: z.boolean().refine((v) => v, {
      message: t("auth.error.consentRequired"),
    }),
    consentMarketing: z.boolean().optional(),
  })
  .refine((data) => data.password === data.passwordConfirm, {
    message: t("auth.error.passwordMismatch"),
    path: ["passwordConfirm"],
  });

export type RegisterValues = z.infer<typeof registerSchema>;
