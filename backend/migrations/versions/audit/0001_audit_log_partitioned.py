"""audit.audit_log — append-only, RANGE-partitioned by ts.

DDL matches .planning/roadmap/wave-0-foundation/phases/
00.3-db-rls-multitenancy.md ("Audit log partitioning" section) and the
ADR-014 amendment 2026-05-19:

  * Partitioned by RANGE (ts), one partition per month
  * Two seeded monthly partitions (May / June 2026) + a DEFAULT partition
    catch-all so writes never fail when the maintenance job is late
  * Append-only by trigger — audit.deny_update_delete() raises EXCEPTION
    on UPDATE or DELETE. Triggers fire on the parent table and inherit
    to every partition automatically.
  * 3-year retention — purges happen by partition DROP, not DELETE,
    because DELETE would be blocked by the same append-only trigger.
    The drop job lives in ops/cron (Wave 1+); Wave 0 ships the partitions
    only.
  * GRANT SELECT, INSERT only to oriion_app on parent + every partition.
    No UPDATE / DELETE grants (the trigger would block them anyway, but
    revoking at the privilege layer is good defence-in-depth).

Revision IDs
------------
Revision ID: audit_0001_audit_log_partitioned
Down revision: _shared_0002_current_user_id_helper
Branch label: audit
Create date: 2026-05-19
"""

from __future__ import annotations

from alembic import op

revision: str = "audit_0001_audit_log_partitioned"
down_revision: str | None = "_shared_0002_current_user_id_helper"
branch_labels: tuple[str, ...] = ("audit",)
depends_on: str | None = None


# Seed partitions for the first two operational months. The maintenance
# job in Wave 1+ will pre-create the next 3 months on a rolling basis;
# any miss falls into audit_log_default and gets re-partitioned offline.
_SEED_PARTITIONS: tuple[tuple[str, str, str], ...] = (
    ("audit_log_2026_05", "2026-05-01", "2026-06-01"),
    ("audit_log_2026_06", "2026-06-01", "2026-07-01"),
)


def upgrade() -> None:
    # ── Parent partitioned table ──────────────────────────────────────
    # Composite PK (id, ts) is required because ts is the partition key;
    # Postgres mandates every column of the partition key be in every
    # UNIQUE / PRIMARY KEY constraint.
    op.execute(
        """
        CREATE TABLE audit.audit_log (
            id              uuid NOT NULL DEFAULT gen_random_uuid(),
            ts              timestamptz NOT NULL DEFAULT now(),
            actor_type      text NOT NULL
                CHECK (actor_type IN ('user','agent','system')),
            actor_id        uuid,
            action          text NOT NULL,
            resource_type   text,
            resource_id     uuid,
            cell_id         uuid,
            workspace_id    uuid,
            payload         jsonb,
            ip              inet,
            user_agent      text,
            PRIMARY KEY (id, ts)
        )
        PARTITION BY RANGE (ts);
        """
    )

    # ── Monthly seed partitions + DEFAULT catch-all ───────────────────
    for name, lo, hi in _SEED_PARTITIONS:
        op.execute(
            f"""
            CREATE TABLE audit.{name}
                PARTITION OF audit.audit_log
                FOR VALUES FROM ('{lo}') TO ('{hi}');
            """
        )
    op.execute(
        """
        CREATE TABLE audit.audit_log_default
            PARTITION OF audit.audit_log
            DEFAULT;
        """
    )

    # ── Indexes on the parent (propagate to every partition) ──────────
    op.execute("CREATE INDEX audit_log_ts_idx ON audit.audit_log (ts DESC);")
    op.execute(
        """
        CREATE INDEX audit_log_actor_id_ts_idx
            ON audit.audit_log (actor_id, ts DESC)
            WHERE actor_id IS NOT NULL;
        """
    )
    op.execute("CREATE INDEX audit_log_action_ts_idx ON audit.audit_log (action, ts DESC);")
    op.execute(
        """
        CREATE INDEX audit_log_cell_id_ts_idx
            ON audit.audit_log (cell_id, ts DESC)
            WHERE cell_id IS NOT NULL;
        """
    )
    op.execute(
        """
        CREATE INDEX audit_log_workspace_id_ts_idx
            ON audit.audit_log (workspace_id, ts DESC)
            WHERE workspace_id IS NOT NULL;
        """
    )

    # ── Append-only trigger function ──────────────────────────────────
    # ADR-014 amendment 2026-05-19: every audit row is immutable.
    # The trigger raises an EXCEPTION on UPDATE / DELETE so even a DBA
    # connection (without bypassrls) hits the wall. Retention purges
    # use DROP TABLE on stale partitions instead.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION audit.deny_update_delete()
        RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'audit.audit_log is append-only';
        END;
        $$;
        """
    )

    op.execute(
        """
        CREATE TRIGGER audit_log_deny_update
            BEFORE UPDATE ON audit.audit_log
            FOR EACH ROW EXECUTE FUNCTION audit.deny_update_delete();
        """
    )
    op.execute(
        """
        CREATE TRIGGER audit_log_deny_delete
            BEFORE DELETE ON audit.audit_log
            FOR EACH ROW EXECUTE FUNCTION audit.deny_update_delete();
        """
    )

    # ── COMMENT documenting invariants + retention ────────────────────
    op.execute(
        "COMMENT ON TABLE audit.audit_log IS "
        "'Append-only audit log. INSERT only — UPDATE / DELETE rejected by "
        "audit.deny_update_delete() trigger. RANGE-partitioned monthly by ts; "
        "3-year retention enforced by DROPping stale partitions (per ADR-014 "
        "amendment 2026-05-19).';"
    )

    # ── GRANTs: SELECT + INSERT only on parent ────────────────────────
    # Postgres partitioned-table grants do NOT propagate to existing
    # partitions, so we GRANT on each partition individually. New
    # partitions created by the maintenance job must be granted at
    # creation time (the job templates do this).
    op.execute("GRANT SELECT, INSERT ON audit.audit_log TO oriion_app;")
    for name, _lo, _hi in _SEED_PARTITIONS:
        op.execute(f"GRANT SELECT, INSERT ON audit.{name} TO oriion_app;")
    op.execute("GRANT SELECT, INSERT ON audit.audit_log_default TO oriion_app;")


def downgrade() -> None:
    # Drop triggers first (depend on the function), then the function,
    # then partitions, then the parent. Each DROP IF EXISTS is idempotent
    # so re-running on a partial downgrade is safe.
    op.execute("DROP TRIGGER IF EXISTS audit_log_deny_delete ON audit.audit_log;")
    op.execute("DROP TRIGGER IF EXISTS audit_log_deny_update ON audit.audit_log;")
    op.execute("DROP FUNCTION IF EXISTS audit.deny_update_delete();")

    op.execute("DROP TABLE IF EXISTS audit.audit_log_default;")
    for name, _lo, _hi in _SEED_PARTITIONS:
        op.execute(f"DROP TABLE IF EXISTS audit.{name};")

    op.execute("DROP TABLE IF EXISTS audit.audit_log;")
