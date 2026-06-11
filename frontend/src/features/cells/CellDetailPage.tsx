/**
 * CellDetailPage — metadata + recent-tasks surface for a single cell.
 * Sets the active cell on mount so the task-submit flow knows its context.
 * Wave-0: the "recent tasks" tab is an empty placeholder (no list endpoint yet).
 */
import { useEffect } from "react";
import { Link, useParams } from "@tanstack/react-router";
import { Breadcrumb, Button, Card, EmptyState, Skeleton, Tabs } from "@/components/ui";
import { t } from "@/lib/i18n";
import type { Cell } from "@/api/cells";
import { useActiveCellStore } from "@/stores/active-cell";
import { useCell } from "./hooks";
import { formatDate } from "./format";

function MetadataRow({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex flex-col gap-0.5 sm:flex-row sm:gap-4">
      <dt className="w-40 shrink-0 text-sm font-medium text-secondary">{label}</dt>
      <dd className={mono ? "text-sm text-primary font-mono break-all" : "text-sm text-primary"}>
        {value}
      </dd>
    </div>
  );
}

function CellDetail({ cell }: { cell: Cell }) {
  return (
    <div className="flex flex-col gap-6">
      <Breadcrumb
        items={[{ label: t("cells.title"), href: "/cells" }, { label: cell.display_name }]}
      />

      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-3xl font-bold text-primary">{cell.display_name}</h1>
        <Button asChild variant="primary">
          <Link to="/cells/$cellId/tasks/new" params={{ cellId: cell.id }}>
            {t("cells.detail.newTask")}
          </Link>
        </Button>
      </div>

      <Card variant="outlined" padding="md">
        <Card.Header>
          <h2 className="text-lg font-medium text-primary">{t("cells.detail.metadata")}</h2>
        </Card.Header>
        <Card.Body className="mt-4">
          <dl className="flex flex-col gap-3">
            <MetadataRow label={t("cells.detail.slug")} value={cell.slug} mono />
            <MetadataRow
              label={t("cells.col.template")}
              value={cell.vertical_template_slug ?? t("cells.dash")}
            />
            <MetadataRow label={t("cells.col.created")} value={formatDate(cell.created_at)} />
          </dl>
        </Card.Body>
      </Card>

      <Tabs defaultValue="recent-tasks">
        <Tabs.List>
          <Tabs.Trigger value="recent-tasks">{t("cells.detail.recentTasks")}</Tabs.Trigger>
        </Tabs.List>
        <Tabs.Content value="recent-tasks">
          <EmptyState title={t("cells.detail.tasksEmpty")} />
        </Tabs.Content>
      </Tabs>
    </div>
  );
}

export function CellDetailPage() {
  const { cellId } = useParams({ strict: false });
  const setActiveCell = useActiveCellStore((s) => s.setActiveCell);
  const { data: cell, isLoading, isError, refetch } = useCell(cellId);

  useEffect(() => {
    if (cellId) setActiveCell(cellId);
  }, [cellId, setActiveCell]);

  if (isError) {
    return (
      <div className="flex flex-col gap-6">
        <Breadcrumb items={[{ label: t("cells.title"), href: "/cells" }]} />
        <h1 className="text-3xl font-bold text-primary">{t("cells.error.detail")}</h1>
        <EmptyState
          variant="danger"
          title={t("cells.error.detail")}
          action={{
            label: t("common.retry"),
            onClick: () => {
              void refetch();
            },
          }}
        />
      </div>
    );
  }

  if (isLoading || !cell) {
    return (
      <div className="flex flex-col gap-6" aria-busy="true">
        <Breadcrumb items={[{ label: t("cells.title"), href: "/cells" }]} />
        <Skeleton className="h-9 w-64" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  return <CellDetail cell={cell} />;
}
