/**
 * Task-submission form schema (C10).
 *
 * The form is intentionally generic: any non-empty prompt up to the backend's
 * 4000-char ceiling is accepted. The "title" sent to the API is derived from
 * the prompt in the submit hook, so the form itself only validates `prompt`.
 */
import { z } from "zod";
import { t } from "@/lib/i18n";

/** Hard ceiling mirrored by the Textarea `maxLength` in the page. */
export const PROMPT_MAX_LENGTH = 4000;

export const taskSubmitSchema = z.object({
  prompt: z
    .string()
    .min(1, t("tasks.submit.promptRequired"))
    .max(PROMPT_MAX_LENGTH, t("tasks.submit.promptTooLong")),
});

export type TaskSubmitValues = z.infer<typeof taskSubmitSchema>;
