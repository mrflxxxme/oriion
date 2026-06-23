"""billing.subscriptions — cell ↔ plan binding with period + trial state.

Phase 01.3, Wave 1. One subscription per cell (a non-canceled row is unique
per cell). Trial is auto-provisioned on first cell creation (14d / 500-credit
trial_grant — see billing.services.subscription_service.start_trial).

RLS: cell-isolation via _shared.current_cell_id() (returns NULL on empty/invalid
GUC ⇒ default-deny). USING with no WITH CHECK ⇒ Postgres reuses USING as the
INSERT/UPDATE WITH CHECK, so a row's cell_id must equal the active tenant cell
(same pattern as billing.credit_transactions ct_cell_isolation).

plan_slug is a real FK → billing.plans(slug) (same bounded context, ADR-024
permits intra-context FKs).

Revision ID: billing_0003_subscriptions
Down revision: billing_0002_plans
Branch label: billing (continued)
"""

from __future__ import annotations

from alembic import op

revision: str = "billing_0003_subscriptions"
down_revision: str | None = "billing_0002_plans"
branch_labels: tuple[str, ...] | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE billing.subscriptions (
            id                          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            cell_id                     uuid NOT NULL,
            workspace_id                uuid NOT NULL,
            plan_slug                   text NOT NULL
                REFERENCES billing.plans(slug),
            status                      text NOT NULL
                CHECK (status IN ('trial','active','past_due','canceled')),
            period_start                timestamptz NOT NULL DEFAULT now(),
            period_end                  timestamptz NOT NULL,
            trial_ends_at               timestamptz NULL,
            credits_granted_this_period numeric(12,4) NOT NULL DEFAULT 0,
            created_at                  timestamptz NOT NULL DEFAULT now(),
            updated_at                  timestamptz NOT NULL DEFAULT now()
        );
        """
    )

    # One active (non-canceled) subscription per cell.
    op.execute(
        """
        CREATE UNIQUE INDEX subscriptions_one_active_per_cell
            ON billing.subscriptions (cell_id)
            WHERE status <> 'canceled';
        """
    )
    op.execute("CREATE INDEX ix_subscriptions_cell ON billing.subscriptions (cell_id);")

    op.execute(
        "COMMENT ON TABLE billing.subscriptions IS "
        "'Cell↔plan subscription with billing period + trial state (ADR-008). "
        "Cell-isolated via RLS. Rollover/expiry deferred (Wave-1 grants valid "
        "within period only).';"
    )

    op.execute(
        """
        CREATE TRIGGER subscriptions_set_updated_at
            BEFORE UPDATE ON billing.subscriptions
            FOR EACH ROW EXECUTE FUNCTION _shared.set_updated_at();
        """
    )

    op.execute("ALTER TABLE billing.subscriptions ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE billing.subscriptions FORCE  ROW LEVEL SECURITY;")
    op.execute(
        """
        CREATE POLICY sub_cell_isolation ON billing.subscriptions
            USING (cell_id = _shared.current_cell_id());
        """
    )

    op.execute("GRANT SELECT, INSERT, UPDATE ON billing.subscriptions TO oriion_app;")


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS sub_cell_isolation ON billing.subscriptions;")
    op.execute("DROP TRIGGER IF EXISTS subscriptions_set_updated_at ON billing.subscriptions;")
    op.execute("DROP TABLE IF EXISTS billing.subscriptions;")
