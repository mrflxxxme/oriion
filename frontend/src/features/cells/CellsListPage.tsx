/**
 * CellsListPage — the authenticated landing surface. Lists every cell across
 * the user's workspaces in a sortable table. Explicitly handles the three
 * query states (loading / error / empty). "Создать ячейку" is Wave-1 gated
 * and therefore rendered disabled.
 */
import { useMemo, useState } from "react";
import { Link } from "@tanstack/react-router";
import { createColumnHelper, type ColumnDef } from "@tanstack/react-table";
import { Badge, Breadcrumb, Button, EmptyState, Pagination, Table } from "@/components/ui";
import { t } from "@/lib/i18n";
import type { Cell } from "@/api/cells";
import { useCellsList } from "./hooks";
import { formatDate } from "./format";

const PAGE_SIZE = 25;

const columnHelper = createColumnHelper<Cell>();

function useCellColumns(): ColumnDef<Cell>[] {
  return useMemo(
    () =>
      [
        columnHelper.accessor("display_name", {
          header: t("cells.col.name"),
          cell: (info) => (
            <Link
              to="/cells/$cellId"
              params={{ cellId: info.row.original.id }}
              className="font-medium text-cta underline-offset-4 hover:underline focus-visible:outline-none focus-visible:shadow-focus-ring rounded-sm"
            >
              {info.getValue()}
            </Link>
          ),
        }),
        columnHelper.accessor("vertical_template_slug", {
          header: t("cells.col.template"),
          cell: (info) => {
            const slug = info.getValue();
            return slug ? (
              <Badge variant="default">{slug}</Badge>
            ) : (
              <span className="text-tertiary">{t("cells.dash")}</span>
            );
          },
        }),
        columnHelper.accessor("created_at", {
          header: t("cells.col.created"),
          cell: (info) => formatDate(info.getValue()),
        }),
      ] as ColumnDef<Cell>[],
    [],
  );
}

export function CellsListPage() {
  const columns = useCellColumns();
  const { data, isLoading, isError, refetch } = useCellsList();
  const [page, setPage] = useState(1);

  const cells = useMemo(() => data ?? [], [data]);
  const totalPages = Math.max(1, Math.ceil(cells.length / PAGE_SIZE));
  const pageCells = useMemo(
    () => cells.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE),
    [cells, page],
  );

  return (
    <div className="flex flex-col gap-6">
      <Breadcrumb items={[{ label: t("cells.title") }]} />

      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-3xl font-bold text-primary">{t("cells.title")}</h1>
        <Button
          variant="primary"
          disabled
          aria-disabled
          title={t("cells.createDisabled")}
          aria-label={`${t("cells.create")} — ${t("cells.createDisabled")}`}
        >
          {t("cells.create")}
        </Button>
      </div>

      {isError ? (
        <EmptyState
          variant="danger"
          title={t("cells.error.list")}
          action={{
            label: t("common.retry"),
            onClick: () => {
              void refetch();
            },
          }}
        />
      ) : !isLoading && cells.length === 0 ? (
        <EmptyState title={t("cells.empty.title")} description={t("cells.empty.description")} />
      ) : (
        <>
          <Table<Cell> columns={columns} data={pageCells} sortable loading={isLoading} />
          {totalPages > 1 ? (
            <Pagination
              currentPage={page}
              totalPages={totalPages}
              pageSize={PAGE_SIZE}
              onPageChange={setPage}
              className="justify-end"
            />
          ) : null}
        </>
      )}
    </div>
  );
}
