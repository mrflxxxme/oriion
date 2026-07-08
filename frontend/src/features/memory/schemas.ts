/**
 * Add-memory form schema — shared shape for both cell- and role-memory forms.
 * `kind` is validated as non-empty here; the concrete literal union (Cell- vs
 * RoleMemoryKind) is enforced by the `<Select>` options passed at the call
 * site, so a value reaching submit is always one of the allowed kinds.
 */
import { z } from "zod";
import { t } from "@/lib/i18n";

/** Mirrors `MemoryEntryCreate.content` / `RoleMemoryEntryCreate.content` (backend/src/memory/schemas.py). */
export const CONTENT_MAX_LENGTH = 8000;
/** Mirrors `title: str | None = Field(max_length=200)`. */
export const TITLE_MAX_LENGTH = 200;

export const memoryFormSchema = z.object({
  kind: z.string().min(1, t("memory.add.kindRequired")),
  title: z.string().max(TITLE_MAX_LENGTH, t("memory.add.titleTooLong")),
  content: z
    .string()
    .min(1, t("memory.add.contentRequired"))
    .max(CONTENT_MAX_LENGTH, t("memory.add.contentTooLong")),
  containsPii: z.boolean(),
});

export type MemoryFormValues = z.infer<typeof memoryFormSchema>;
