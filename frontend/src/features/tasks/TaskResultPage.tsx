/**
 * TaskResultPage — watches a task end-to-end (C12). Three tabs:
 *  - Прогресс: the SSE-driven agent step-cards + log (TaskProgressStream).
 *  - Результат: the 3 markdown artifacts (matrix/analysis/brief), sanitized via
 *    react-markdown (never dangerouslySetInnerHTML).
 *  - Стоимость: per-agent cost breakdown (from the SSE delegation events).
 *
 * Data: useTask polls metadata (5s while running); useTaskStream subscribes to
 * the SSE ledger (drain-replay covers a late subscriber on an already-finished
 * task). A cancel confirm Dialog appears only while running.
 */
import { useMemo, useState } from "react";
import { useParams } from "@tanstack/react-router";
import { createColumnHelper, type ColumnDef } from "@tanstack/react-table";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Badge,
  Breadcrumb,
  Button,
  Dialog,
  EmptyState,
  Skeleton,
  Table,
  Tabs,
} from "@/components/ui";
import type { BadgeProps } from "@/components/ui";
import { tasksApi, type Artifact } from "@/api/tasks";
import { ApiException } from "@/api/client";
import { toast } from "@/components/ui";
import { t } from "@/lib/i18n";
import { useTask, useTaskStream } from "./hooks";
import { TaskProgressStream } from "./TaskProgressStream";
import type { CostRow } from "./progress-reducer";

const TERMINAL = new Set(["succeeded", "completed", "failed", "cancelled"]);

const STATUS_BADGE: Record<string, { variant: BadgeProps["variant"]; label: string }> = {
  queued: { variant: "default", label: "В очереди" },
  running: { variant: "warning", label: "Выполняется" },
  succeeded: { variant: "success", label: "Завершено" },
  completed: { variant: "success", label: "Завершено" },
  failed: { variant: "danger", label: "Ошибка" },
  cancelled: { variant: "default", label: "Отменено" },
};

const ARTIFACT_LABEL: Record<string, string> = {
  matrix: "Матрица исследования",
  analysis: "Аналитика (рабочий документ)",
  brief: "Бриф и контент-план",
};

// Final deliverables are shown prominently; intermediate working documents
// (the analyst's inter-step output + any unknown future types) collapse into
// a secondary disclosure so the Результат tab reads as a clean human answer.
const FINAL_ARTIFACT_TYPES = new Set(["matrix", "brief"]);

const costColumnHelper = createColumnHelper<CostRow>();
const COST_COLUMNS = [
  costColumnHelper.accessor("label", { header: "Агент", cell: (i) => i.getValue() }),
  costColumnHelper.accessor("costCredits", {
    header: "T-кредиты",
    cell: (i) => i.getValue().toFixed(4),
  }),
  costColumnHelper.accessor("tokens", { header: "Токены", cell: (i) => i.getValue() }),
] as ColumnDef<CostRow>[];

// Demote artifact-internal headings (h1→h3…) so they never compete with the
// page <h1> / section <h2> (a11y heading order), and harden any LLM-emitted
// links. react-markdown v10 already escapes raw HTML + sanitizes URL schemes.
const MARKDOWN_COMPONENTS: Components = {
  a: ({ node: _node, ...props }) => (
    <a {...props} target="_blank" rel="noopener noreferrer nofollow" />
  ),
  h1: ({ node: _node, ...props }) => <h3 {...props} />,
  h2: ({ node: _node, ...props }) => <h4 {...props} />,
  h3: ({ node: _node, ...props }) => <h5 {...props} />,
};

function ArtifactSection({ artifact }: { artifact: Artifact }) {
  const label = ARTIFACT_LABEL[artifact.type] ?? artifact.type;
  return (
    <section className="flex flex-col gap-2">
      <h2 className="text-lg font-semibold text-primary">{label}</h2>
      <div className="max-w-none text-sm text-secondary [&_h3]:mt-4 [&_h3]:text-base [&_h3]:font-semibold [&_h3]:text-primary [&_h4]:mt-3 [&_h4]:font-semibold [&_h4]:text-primary [&_li]:ml-4 [&_li]:list-disc [&_strong]:text-primary [&_table]:w-full [&_td]:border [&_td]:border-default [&_td]:px-2 [&_td]:py-1 [&_th]:border [&_th]:border-default [&_th]:px-2 [&_th]:py-1 [&_a]:text-cta-hover [&_a]:underline">
        <ReactMarkdown remarkPlugins={[remarkGfm]} components={MARKDOWN_COMPONENTS}>
          {artifact.path_or_inline}
        </ReactMarkdown>
      </div>
    </section>
  );
}

export function TaskResultPage() {
  const params = useParams({ strict: false });
  const cellId = params.cellId ?? "";
  const taskId = params.taskId ?? "";
  const { data: task, isLoading, isError, refetch } = useTask(cellId, taskId);
  const isRunning = !!task && !TERMINAL.has(task.status);
  const { progress, streamError } = useTaskStream(cellId, taskId, true);
  const [cancelOpen, setCancelOpen] = useState(false);
  const [cancelling, setCancelling] = useState(false);

  const artifacts = progress.artifacts;
  const statusKey = task?.status ?? "queued";
  const badge = STATUS_BADGE[statusKey] ?? STATUS_BADGE.queued;

  const title = useMemo(() => {
    const raw = task?.title ?? "Задача";
    return raw.length > 80 ? `${raw.slice(0, 80)}…` : raw;
  }, [task?.title]);

  async function handleCancel() {
    setCancelling(true);
    try {
      await tasksApi.cancel(cellId, taskId);
      await refetch();
      setCancelOpen(false);
    } catch (error) {
      toast.error(
        error instanceof ApiException ? error.error.message : "Не удалось отменить задачу.",
      );
    } finally {
      setCancelling(false);
    }
  }

  if (isLoading) {
    return (
      <div className="flex flex-col gap-4">
        <Skeleton height={28} width="40%" />
        <Skeleton height={200} />
      </div>
    );
  }

  if (isError || !task) {
    return (
      <EmptyState
        variant="danger"
        title="Не удалось загрузить задачу"
        action={{
          label: t("common.retry"),
          onClick: () => {
            void refetch();
          },
        }}
      />
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <Breadcrumb
        items={[{ label: t("cells.title"), href: "/cells" }, { label: t("tasks.result.region") }]}
      />

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <h1 className="text-3xl font-bold text-primary">{title}</h1>
          <Badge variant={badge?.variant}>{badge?.label}</Badge>
        </div>
        {isRunning ? (
          <Button
            variant="destructive"
            onClick={() => {
              setCancelOpen(true);
            }}
          >
            {t("tasks.result.cancel")}
          </Button>
        ) : null}
      </div>

      <Tabs defaultValue="progress">
        <Tabs.List>
          <Tabs.Trigger value="progress">{t("tasks.result.tab.progress")}</Tabs.Trigger>
          <Tabs.Trigger value="result">{t("tasks.result.tab.result")}</Tabs.Trigger>
          <Tabs.Trigger value="cost">{t("tasks.result.tab.cost")}</Tabs.Trigger>
        </Tabs.List>

        <Tabs.Content value="progress">
          <TaskProgressStream progress={progress} isRunning={isRunning} streamError={streamError} />
        </Tabs.Content>

        <Tabs.Content value="result">
          {artifacts.length === 0 ? (
            <EmptyState
              title={isRunning ? "Результат ещё готовится" : "Результат недоступен"}
              {...(isRunning
                ? { description: "Артефакты появятся, когда команда агентов завершит работу." }
                : {})}
            />
          ) : (
            <div
              role="region"
              aria-label={t("tasks.result.region")}
              className="flex flex-col gap-8"
            >
              {artifacts
                .filter((artifact) => FINAL_ARTIFACT_TYPES.has(artifact.type))
                .map((artifact) => (
                  <ArtifactSection key={artifact.id ?? artifact.type} artifact={artifact} />
                ))}
              {artifacts.some((artifact) => !FINAL_ARTIFACT_TYPES.has(artifact.type)) ? (
                <details className="rounded-md border border-default p-4">
                  <summary className="cursor-pointer text-sm font-medium text-secondary hover:text-primary focus-visible:outline-none focus-visible:shadow-focus-ring">
                    Промежуточные материалы
                  </summary>
                  <div className="mt-4 flex flex-col gap-8">
                    {artifacts
                      .filter((artifact) => !FINAL_ARTIFACT_TYPES.has(artifact.type))
                      .map((artifact) => (
                        <ArtifactSection key={artifact.id ?? artifact.type} artifact={artifact} />
                      ))}
                  </div>
                </details>
              ) : null}
            </div>
          )}
        </Tabs.Content>

        <Tabs.Content value="cost">
          <div className="flex flex-col gap-4">
            <Table<CostRow>
              columns={COST_COLUMNS}
              data={progress.costRows}
              emptyState={<EmptyState title="Данные о стоимости появятся после выполнения" />}
            />
            <p className="text-sm text-tertiary">
              Итого: {Number(task.total_cost_credits ?? 0).toFixed(4)} T-кредитов ·{" "}
              {task.total_input_tokens ?? 0} + {task.total_output_tokens ?? 0} токенов
            </p>
          </div>
        </Tabs.Content>
      </Tabs>

      <Dialog open={cancelOpen} onOpenChange={setCancelOpen}>
        <Dialog.Content size="sm">
          <Dialog.Header>
            <Dialog.Title>{t("tasks.result.cancel")}</Dialog.Title>
            <Dialog.Description>Задачу нельзя будет возобновить.</Dialog.Description>
          </Dialog.Header>
          <Dialog.Footer>
            <Button
              variant="secondary"
              onClick={() => {
                setCancelOpen(false);
              }}
            >
              {t("common.cancel")}
            </Button>
            <Button variant="destructive" loading={cancelling} onClick={() => void handleCancel()}>
              {t("tasks.result.cancel")}
            </Button>
          </Dialog.Footer>
        </Dialog.Content>
      </Dialog>
    </div>
  );
}
