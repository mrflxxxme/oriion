/**
 * MemoryAddForm — manual «запомни» form shared by cell- and role-memory
 * sections. POSTing through this form always yields `source: "manual"`
 * server-side (backend/src/memory/schemas.py docstring) — there is no
 * PATCH endpoint, so "editing" an entry is delete + prefill-add (owned by
 * the parent section, see `MemorySection.tsx`).
 */
import { useId } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import type { SelectOption } from "@/components/ui";
import { Button, Checkbox, Input, Select, Textarea } from "@/components/ui";
import { t } from "@/lib/i18n";
import { memoryFormSchema, type MemoryFormValues, CONTENT_MAX_LENGTH } from "./schemas";

export interface MemoryAddPayload {
  kind: string;
  title?: string;
  content: string;
  contains_pii: boolean;
}

export interface MemoryAddFormProps {
  kindOptions: SelectOption[];
  defaultKind: string;
  onSubmit: (payload: MemoryAddPayload) => void;
  isPending: boolean;
  /** Prefilled content when re-adding after a delete ("edit" = delete + prefill-add). */
  prefill?: MemoryAddPayload;
}

export function MemoryAddForm({
  kindOptions,
  defaultKind,
  onSubmit,
  isPending,
  prefill,
}: MemoryAddFormProps) {
  const kindId = useId();
  const titleId = useId();
  const contentId = useId();
  const contentErrorId = useId();
  const piiId = useId();

  const form = useForm<MemoryFormValues>({
    resolver: zodResolver(memoryFormSchema),
    defaultValues: {
      kind: prefill?.kind ?? defaultKind,
      title: prefill?.title ?? "",
      content: prefill?.content ?? "",
      containsPii: prefill?.contains_pii ?? false,
    },
    mode: "onSubmit",
  });

  const onValid = (values: MemoryFormValues): void => {
    onSubmit({
      kind: values.kind,
      ...(values.title.trim() ? { title: values.title.trim() } : {}),
      content: values.content,
      contains_pii: values.containsPii,
    });
    form.reset({ kind: values.kind, title: "", content: "", containsPii: false });
  };

  const contentError = form.formState.errors.content?.message;

  return (
    <form
      onSubmit={(e) => void form.handleSubmit(onValid)(e)}
      noValidate
      className="flex flex-col gap-4 rounded-md border border-default bg-surface p-4"
    >
      <div className="flex flex-col gap-1.5">
        <label htmlFor={kindId} className="text-sm font-medium text-primary">
          {t("memory.add.kindLabel")}
        </label>
        <Controller
          control={form.control}
          name="kind"
          render={({ field }) => (
            <Select
              id={kindId}
              options={kindOptions}
              value={field.value}
              onValueChange={field.onChange}
              name={field.name}
            />
          )}
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor={titleId} className="text-sm font-medium text-primary">
          {t("memory.add.titleLabel")}{" "}
          <span className="font-normal text-tertiary">{t("common.optional")}</span>
        </label>
        <Input
          id={titleId}
          placeholder={t("memory.add.titlePlaceholder")}
          {...form.register("title")}
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor={contentId} className="text-sm font-medium text-primary">
          {t("memory.add.contentLabel")}
        </label>
        <Controller
          control={form.control}
          name="content"
          render={({ field }) => (
            <Textarea
              id={contentId}
              rows={3}
              autosize
              maxLength={CONTENT_MAX_LENGTH}
              placeholder={t("memory.add.contentPlaceholder")}
              invalid={contentError !== undefined}
              aria-describedby={contentError !== undefined ? contentErrorId : undefined}
              name={field.name}
              ref={field.ref}
              value={field.value}
              onChange={field.onChange}
              onBlur={field.onBlur}
            />
          )}
        />
        {contentError !== undefined ? (
          <p id={contentErrorId} role="alert" className="text-sm text-danger-600">
            {contentError}
          </p>
        ) : null}
      </div>

      <Controller
        control={form.control}
        name="containsPii"
        render={({ field }) => (
          <Checkbox
            id={piiId}
            label={t("memory.add.piiLabel")}
            checked={field.value}
            onCheckedChange={(checked) => {
              field.onChange(checked === true);
            }}
          />
        )}
      />

      <Button type="submit" loading={isPending} className="self-start">
        {t("memory.add.submit")}
      </Button>
    </form>
  );
}
