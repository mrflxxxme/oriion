/**
 * OnboardingPage (Phase 01.12) — a 3-step wizard that takes a freshly
 * registered user from "just signed up" to "watching my first task run".
 *
 * ADR-022 hybrid: fixed wizard structure with optional LLM hint text (the
 * per-preset demo prompt is a static, proven scenario, not an LLM call).
 *
 *   1. Welcome — what's about to happen (the trial cell already auto-spawned
 *      at register, so there's nothing to create here).
 *   2. Choose a preset — provisions the picked team into the cell via
 *      POST /cells/{cellId}/teams (all 3 catalog presets).
 *   3. First task — a prefilled demo prompt per preset; submit creates + runs
 *      the task, records it for the dashboard, and lands on the live progress
 *      page. The dashboard is one nav-click away from there.
 *
 * Every data-driven surface (the cell lookup) has loading / error states;
 * "Пропустить настройку" is always available as an escape hatch to /dashboard.
 */
import { useState, type ReactNode } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useNavigate } from "@tanstack/react-router";
import {
  Badge,
  Breadcrumb,
  Button,
  Card,
  EmptyState,
  RadioGroup,
  Skeleton,
  Textarea,
} from "@/components/ui";
import type { RadioOption } from "@/components/ui";
import { t, type I18nKey } from "@/lib/i18n";
import {
  taskSubmitSchema,
  type TaskSubmitValues,
  PROMPT_MAX_LENGTH,
} from "@/features/tasks/schemas";
import { ONBOARDING_PRESETS, findPreset, type PresetKey } from "./presets";
import { useCellsStatus, useCurrentCellId, useProvisionPreset, useSeedFirstTask } from "./hooks";

type Step = 1 | 2 | 3;

const STEP_BADGE: Record<Step, I18nKey> = {
  1: "onboarding.stepBadge1",
  2: "onboarding.stepBadge2",
  3: "onboarding.stepBadge3",
};

function WizardShell({ step, children }: { step: Step; children: ReactNode }) {
  const navigate = useNavigate();
  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-6">
      <Breadcrumb items={[{ label: t("onboarding.crumb") }]} />
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-3xl font-bold text-primary">{t("onboarding.title")}</h1>
        <Badge variant="primary" size="md">
          {t(STEP_BADGE[step])}
        </Badge>
      </div>
      {children}
      <div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => {
            void navigate({ to: "/dashboard" });
          }}
        >
          {t("onboarding.skip")}
        </Button>
      </div>
    </div>
  );
}

function WelcomeStep({ onNext }: { onNext: () => void }) {
  return (
    <Card variant="outlined" padding="lg">
      <Card.Body className="flex flex-col gap-4">
        <h2 className="text-xl font-semibold text-primary">{t("onboarding.welcome.title")}</h2>
        <p className="text-sm text-secondary">{t("onboarding.welcome.description")}</p>
      </Card.Body>
      <Card.Footer className="mt-6 justify-end">
        <Button onClick={onNext}>{t("onboarding.welcome.next")}</Button>
      </Card.Footer>
    </Card>
  );
}

function PresetStep({
  cellId,
  onBack,
  onProvisioned,
}: {
  cellId: string | undefined;
  onBack: () => void;
  onProvisioned: (preset: PresetKey) => void;
}) {
  const [selected, setSelected] = useState<PresetKey>(
    ONBOARDING_PRESETS[0]?.key ?? "productivity-core",
  );
  const provision = useProvisionPreset(cellId);

  const options: RadioOption[] = ONBOARDING_PRESETS.map((preset) => ({
    value: preset.key,
    label: t(preset.titleKey),
  }));

  const selectedPreset = findPreset(selected);

  return (
    <Card variant="outlined" padding="lg">
      <Card.Body className="flex flex-col gap-5">
        <div className="flex flex-col gap-1">
          <h2 className="text-xl font-semibold text-primary">{t("onboarding.preset.title")}</h2>
          <p className="text-sm text-secondary">{t("onboarding.preset.description")}</p>
        </div>

        <RadioGroup
          options={options}
          value={selected}
          onValueChange={(value) => {
            setSelected(value as PresetKey);
          }}
          aria-label={t("onboarding.preset.title")}
        />

        <p className="rounded-md bg-page p-4 text-sm text-secondary">
          {t(selectedPreset.descriptionKey)}
        </p>
      </Card.Body>
      <Card.Footer className="mt-6 justify-between">
        <Button variant="ghost" onClick={onBack}>
          {t("onboarding.preset.back")}
        </Button>
        <Button
          loading={provision.isPending}
          onClick={() => {
            provision.mutate(selected, {
              onSuccess: () => {
                onProvisioned(selected);
              },
            });
          }}
        >
          {t("onboarding.preset.next")}
        </Button>
      </Card.Footer>
    </Card>
  );
}

function FirstTaskStep({
  cellId,
  preset,
  onBack,
}: {
  cellId: string | undefined;
  preset: PresetKey;
  onBack: () => void;
}) {
  const presetDef = findPreset(preset);
  const demoPrompt = t(presetDef.demoPromptKey);
  const demoTitle = t(presetDef.demoTitleKey);
  const { submit, isPending } = useSeedFirstTask(cellId);

  const form = useForm<TaskSubmitValues>({
    resolver: zodResolver(taskSubmitSchema),
    defaultValues: { prompt: demoPrompt },
    mode: "onSubmit",
  });

  const promptError = form.formState.errors.prompt?.message;

  const onValid = (values: TaskSubmitValues): void => {
    submit({ title: demoTitle, prompt: values.prompt });
  };

  return (
    <Card variant="outlined" padding="lg">
      <form onSubmit={(e) => void form.handleSubmit(onValid)(e)} noValidate>
        <Card.Body className="flex flex-col gap-5">
          <div className="flex flex-col gap-1">
            <h2 className="text-xl font-semibold text-primary">{t("onboarding.task.title")}</h2>
            <p className="text-sm text-secondary">{t("onboarding.task.description")}</p>
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="onboarding-prompt" className="text-sm font-medium text-primary">
              {t("onboarding.task.prompt")}
            </label>
            <Controller
              control={form.control}
              name="prompt"
              render={({ field }) => (
                <Textarea
                  id="onboarding-prompt"
                  rows={6}
                  autosize
                  maxLength={PROMPT_MAX_LENGTH}
                  invalid={promptError !== undefined}
                  aria-describedby={
                    promptError !== undefined ? "onboarding-prompt-error" : undefined
                  }
                  name={field.name}
                  ref={field.ref}
                  value={typeof field.value === "string" ? field.value : ""}
                  onChange={field.onChange}
                  onBlur={field.onBlur}
                />
              )}
            />
            {promptError !== undefined ? (
              <p id="onboarding-prompt-error" role="alert" className="text-sm text-danger-600">
                {promptError}
              </p>
            ) : null}
          </div>
        </Card.Body>
        <Card.Footer className="mt-6 justify-between">
          <Button type="button" variant="ghost" onClick={onBack}>
            {t("onboarding.task.back")}
          </Button>
          <Button type="submit" loading={isPending}>
            {t("onboarding.task.submit")}
          </Button>
        </Card.Footer>
      </form>
    </Card>
  );
}

export function OnboardingPage() {
  const [step, setStep] = useState<Step>(1);
  const [preset, setPreset] = useState<PresetKey | null>(null);
  const cellId = useCurrentCellId();
  const { isLoading, isError, hasCell } = useCellsStatus();

  if (isLoading) {
    return (
      <WizardShell step={step}>
        <div aria-busy="true" className="flex flex-col gap-3">
          <Skeleton height={120} />
        </div>
      </WizardShell>
    );
  }

  if (isError || !hasCell) {
    return (
      <WizardShell step={step}>
        <EmptyState variant="danger" title={t("onboarding.error.cell")} />
      </WizardShell>
    );
  }

  return (
    <WizardShell step={step}>
      {step === 1 ? (
        <WelcomeStep
          onNext={() => {
            setStep(2);
          }}
        />
      ) : null}
      {step === 2 ? (
        <PresetStep
          cellId={cellId}
          onBack={() => {
            setStep(1);
          }}
          onProvisioned={(picked) => {
            setPreset(picked);
            setStep(3);
          }}
        />
      ) : null}
      {step === 3 && preset ? (
        <FirstTaskStep
          cellId={cellId}
          preset={preset}
          onBack={() => {
            setStep(2);
          }}
        />
      ) : null}
    </WizardShell>
  );
}
