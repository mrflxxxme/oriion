/**
 * DashboardPage (Phase 01.12) — a read-only summary surface over ready APIs:
 *  - Credit balance (GET /billing/balance) — the headline card.
 *  - Recent tasks — the ids this app created (onboarding first-task today),
 *    each re-fetched via the existing per-task GET (see hooks/store for why
 *    there's no list-tasks endpoint). Rows link into the live task-result page.
 *  - Artifacts (GET /artifacts) — the cell's document/asset envelopes.
 *  - A link to the memory panel (01.4-ui, already at /memory).
 *
 * Every section owns its own loading / empty / error state so a single slow or
 * failing query never blanks the whole page.
 */
import { Link } from "@tanstack/react-router";
import { Brain } from "lucide-react";
import { Badge, Breadcrumb, Button, Card, EmptyState, Skeleton, Table } from "@/components/ui";
import type { BadgeProps } from "@/components/ui";
import { createColumnHelper, type ColumnDef } from "@tanstack/react-table";
import { t } from "@/lib/i18n";
import type { ArtifactEnvelope } from "@/api/artifacts";
import { formatCredits, formatDateTime } from "./format";
import {
  useBalance,
  useRecentArtifacts,
  useRecentTaskRefs,
  useRecentTaskSummaries,
  type RecentTaskSummary,
} from "./hooks";

const STATUS_BADGE: Record<string, { variant: BadgeProps["variant"]; label: string }> = {
  queued: { variant: "default", label: "В очереди" },
  running: { variant: "warning", label: "Выполняется" },
  succeeded: { variant: "success", label: "Завершено" },
  completed: { variant: "success", label: "Завершено" },
  failed: { variant: "danger", label: "Ошибка" },
  cancelled: { variant: "default", label: "Отменено" },
};

function BalanceCard() {
  const { data, isLoading, isError } = useBalance();

  return (
    <Card variant="outlined" padding="lg">
      <Card.Header>
        <h2 className="text-lg font-medium text-primary">{t("dashboard.balance.title")}</h2>
      </Card.Header>
      <Card.Body className="mt-4">
        {isLoading ? (
          <Skeleton height={56} width="60%" />
        ) : isError || !data ? (
          <p className="text-sm text-danger-600">{t("dashboard.balance.error")}</p>
        ) : (
          <div className="flex flex-col gap-4">
            <p className="flex items-baseline gap-2">
              <span className="text-4xl font-bold text-primary">
                {formatCredits(data.balance_credits)}
              </span>
              <span className="text-sm text-secondary">{t("dashboard.balance.available")}</span>
            </p>
            <dl className="flex flex-wrap gap-x-8 gap-y-2 text-sm">
              <div className="flex flex-col">
                <dt className="text-tertiary">{t("dashboard.balance.periodUsage")}</dt>
                <dd className="font-medium text-primary">
                  {formatCredits(data.period_usage_credits)}
                </dd>
              </div>
              <div className="flex flex-col">
                <dt className="text-tertiary">{t("dashboard.balance.dailyUsage")}</dt>
                <dd className="font-medium text-primary">
                  {formatCredits(data.daily_usage_credits)}
                </dd>
              </div>
            </dl>
          </div>
        )}
      </Card.Body>
    </Card>
  );
}

function TaskStatusBadge({ summary }: { summary: RecentTaskSummary }) {
  if (summary.isError) {
    return <Badge variant="danger">{t("dashboard.tasks.error")}</Badge>;
  }
  if (summary.isLoading || !summary.task) {
    return <Skeleton height={20} width={80} />;
  }
  const badge = STATUS_BADGE[summary.task.status] ?? STATUS_BADGE.queued;
  return <Badge variant={badge?.variant}>{badge?.label}</Badge>;
}

function RecentTasksSection() {
  const refs = useRecentTaskRefs();
  const summaries = useRecentTaskSummaries(refs);

  return (
    <Card variant="outlined" padding="lg">
      <Card.Header>
        <h2 className="text-lg font-medium text-primary">{t("dashboard.tasks.title")}</h2>
      </Card.Header>
      <Card.Body className="mt-4">
        {refs.length === 0 ? (
          <EmptyState
            title={t("dashboard.tasks.empty.title")}
            description={t("dashboard.tasks.empty.description")}
            action={{
              label: t("dashboard.tasks.empty.action"),
              onClick: () => {
                window.location.assign("/onboarding");
              },
            }}
          />
        ) : (
          <ul className="flex flex-col divide-y divide-default">
            {summaries.map((summary) => (
              <li
                key={summary.ref.taskId}
                className="flex items-center justify-between gap-4 py-3 first:pt-0 last:pb-0"
              >
                <div className="flex min-w-0 flex-col">
                  <Link
                    to="/cells/$cellId/tasks/$taskId"
                    params={{ cellId: summary.ref.cellId, taskId: summary.ref.taskId }}
                    className="truncate text-sm font-medium text-cta-hover underline-offset-4 hover:underline focus-visible:outline-none focus-visible:shadow-focus-ring"
                  >
                    {summary.task?.title ?? summary.ref.title}
                  </Link>
                  <span className="text-xs text-tertiary">
                    {formatDateTime(summary.task?.created_at ?? summary.ref.createdAt)}
                  </span>
                </div>
                <TaskStatusBadge summary={summary} />
              </li>
            ))}
          </ul>
        )}
      </Card.Body>
    </Card>
  );
}

const artifactColumnHelper = createColumnHelper<ArtifactEnvelope>();
const ARTIFACT_COLUMNS = [
  artifactColumnHelper.accessor("title", {
    header: () => t("dashboard.artifacts.col.title"),
    cell: (info) => info.getValue(),
  }),
  artifactColumnHelper.accessor("artifact_type", {
    header: () => t("dashboard.artifacts.col.type"),
    cell: (info) => info.getValue(),
  }),
  artifactColumnHelper.accessor("updated_at", {
    header: () => t("dashboard.artifacts.col.updated"),
    cell: (info) => formatDateTime(info.getValue()),
  }),
] as ColumnDef<ArtifactEnvelope>[];

function ArtifactsSection() {
  const { data, isLoading, isError } = useRecentArtifacts();

  return (
    <Card variant="outlined" padding="lg">
      <Card.Header>
        <h2 className="text-lg font-medium text-primary">{t("dashboard.artifacts.title")}</h2>
      </Card.Header>
      <Card.Body className="mt-4">
        {isError ? (
          <p className="text-sm text-danger-600">{t("dashboard.artifacts.error")}</p>
        ) : (
          <Table<ArtifactEnvelope>
            columns={ARTIFACT_COLUMNS}
            data={data ?? []}
            loading={isLoading}
            emptyState={
              <EmptyState
                title={t("dashboard.artifacts.empty.title")}
                description={t("dashboard.artifacts.empty.description")}
              />
            }
          />
        )}
      </Card.Body>
    </Card>
  );
}

function MemoryLinkCard() {
  return (
    <Card variant="outlined" padding="lg">
      <Card.Body className="flex flex-col items-start gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <Brain className="size-6 text-secondary" aria-hidden="true" />
          <div className="flex flex-col">
            <h2 className="text-lg font-medium text-primary">{t("dashboard.memory.title")}</h2>
            <p className="text-sm text-secondary">{t("dashboard.memory.description")}</p>
          </div>
        </div>
        <Button asChild variant="secondary">
          <Link to="/memory">{t("dashboard.memory.link")}</Link>
        </Button>
      </Card.Body>
    </Card>
  );
}

export function DashboardPage() {
  return (
    <div className="flex flex-col gap-6">
      <Breadcrumb items={[{ label: t("dashboard.crumb") }]} />
      <h1 className="text-3xl font-bold text-primary">{t("dashboard.title")}</h1>

      <div className="grid gap-6 lg:grid-cols-2">
        <BalanceCard />
        <MemoryLinkCard />
      </div>

      <RecentTasksSection />
      <ArtifactsSection />
    </div>
  );
}
