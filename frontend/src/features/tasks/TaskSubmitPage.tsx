/**
 * TaskSubmitPage (C10) — generic task-submission form wired to the live API.
 *
 * Flow on submit (see `useCreateAndRunTask`): create → navigate → fire run()
 * unawaited. The form accepts any prompt; the "Маркет-бриф" chip is a one-click
 * prefill of the proven Wave-0 prompt, nothing more.
 */
import { useId } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useNavigate, useParams } from "@tanstack/react-router";
import { Badge, Breadcrumb, Button, Card, Textarea } from "@/components/ui";
import { t } from "@/lib/i18n";
import { taskSubmitSchema, type TaskSubmitValues, PROMPT_MAX_LENGTH } from "./schemas";
import { useCreateAndRunTask } from "./hooks";

/** Proven Wave-0 prompt the preset chip fills in. */
const PRESET_PROMPT =
  "Запускаем платформу AI-команд для SMB в РФ. Сделай нам market brief + контент-план первого месяца.";

const ROLE_KEYS = [
  "tasks.submit.roleResearcher",
  "tasks.submit.roleAnalyst",
  "tasks.submit.roleWriter",
] as const;

export function TaskSubmitPage() {
  const { cellId } = useParams({ strict: false });
  const navigate = useNavigate();
  const { submit, isPending } = useCreateAndRunTask(cellId ?? "");

  const hintId = useId();
  const errorId = useId();

  const form = useForm<TaskSubmitValues>({
    resolver: zodResolver(taskSubmitSchema),
    defaultValues: { prompt: "" },
    mode: "onSubmit",
  });

  const onValid = (values: TaskSubmitValues): void => {
    submit(values.prompt);
  };

  const promptError = form.formState.errors.prompt?.message;

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-6">
      <Breadcrumb
        items={[
          { label: t("cells.title"), href: "/cells" },
          {
            label: t("cells.detail.recentTasks"),
            ...(cellId ? { href: `/cells/${cellId}` } : {}),
          },
          { label: t("tasks.submit.crumb") },
        ]}
      />

      <h1 className="text-2xl font-semibold text-primary">{t("tasks.submit.title")}</h1>

      <Card variant="outlined" padding="lg">
        <form onSubmit={(e) => void form.handleSubmit(onValid)(e)} noValidate>
          <Card.Body className="flex flex-col gap-5">
            <div className="flex flex-wrap items-center gap-2">
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => {
                  form.setValue("prompt", PRESET_PROMPT, {
                    shouldValidate: false,
                    shouldDirty: true,
                  });
                }}
              >
                {t("tasks.submit.preset")}
              </Button>
            </div>

            <div className="flex flex-col gap-1.5">
              <label htmlFor="task-prompt" className="text-sm font-medium text-primary">
                {t("tasks.submit.prompt")}
              </label>
              <Controller
                control={form.control}
                name="prompt"
                render={({ field }) => (
                  <Textarea
                    id="task-prompt"
                    rows={6}
                    autosize
                    maxLength={PROMPT_MAX_LENGTH}
                    invalid={promptError !== undefined}
                    aria-describedby={promptError !== undefined ? errorId : hintId}
                    name={field.name}
                    ref={field.ref}
                    value={typeof field.value === "string" ? field.value : ""}
                    onChange={field.onChange}
                    onBlur={field.onBlur}
                  />
                )}
              />
              {promptError !== undefined ? (
                <p id={errorId} role="alert" className="text-sm text-danger-600">
                  {promptError}
                </p>
              ) : (
                <p id={hintId} className="text-sm text-tertiary">
                  {t("tasks.submit.promptHint")}
                </p>
              )}
            </div>

            <div className="flex flex-col gap-2">
              <p className="text-sm text-secondary">{t("tasks.submit.pipelineHint")}</p>
              <div className="flex flex-wrap gap-2">
                {ROLE_KEYS.map((key) => (
                  <Badge key={key} variant="info" size="md">
                    {t(key)}
                  </Badge>
                ))}
              </div>
            </div>
          </Card.Body>

          <Card.Footer className="mt-6 flex-col items-stretch gap-3 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm text-tertiary">{t("tasks.submit.costHint")}</p>
            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="ghost"
                onClick={() => {
                  void navigate({
                    to: "/cells/$cellId",
                    params: { cellId: cellId ?? "" },
                  });
                }}
              >
                {t("common.cancel")}
              </Button>
              <Button type="submit" loading={isPending}>
                {t("tasks.submit.submit")}
              </Button>
            </div>
          </Card.Footer>
        </form>
      </Card>
    </div>
  );
}
