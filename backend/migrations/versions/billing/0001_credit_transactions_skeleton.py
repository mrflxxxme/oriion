"""billing.credit_transactions — Wave 0 SKELETON.

Wave 0 inline DDL per contracts/billing/README.md (full billing context lands
in Wave 2-3). Used by llm_gateway.services.billing_service.record_llm_cost
as the second leg of the atomic 3-currency write (per llm-gateway invariant #7).

Invariant: SUM(credit_transactions.amount_rub) == SUM(llm_usage_log.cost_rub)
per cell — enforced by the application service.

Revision ID: billing_0001_credit_transactions_skeleton
Down revision: _shared_0002_current_user_id_helper
Branch label: billing
"""

from __future__ import annotations

from alembic import op

revision: str = "billing_0001_credit_transactions_skeleton"
down_revision: str | None = "_shared_0002_current_user_id_helper"
branch_labels: tuple[str, ...] = ("billing",)
depends_on: str | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE billing.credit_transactions (
            id                     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            cell_id                uuid NOT NULL,
            workspace_id           uuid NOT NULL,
            user_id                uuid NULL,
            task_id                uuid NULL,
            transaction_type       text NOT NULL
                CHECK (transaction_type IN
                    ('debit','credit','refund','trial_grant')),
            amount_rub             numeric(12,4) NOT NULL,
            amount_credits         numeric(12,4) NOT NULL,
            balance_after_credits  numeric(12,4) NOT NULL,
            fx_rate_usd_to_rub     numeric(10,6) NULL,
            provider               text NULL,
            model                  text NULL,
            tokens_input           int  NOT NULL DEFAULT 0,
            tokens_output          int  NOT NULL DEFAULT 0,
            payload                jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at             timestamptz NOT NULL DEFAULT now()
        );
        """
    )

    op.execute(
        "CREATE INDEX ix_credit_tx_cell_created "
        "ON billing.credit_transactions (cell_id, created_at DESC);"
    )
    op.execute(
        "CREATE INDEX ix_credit_tx_workspace_created "
        "ON billing.credit_transactions (workspace_id, created_at DESC);"
    )
    op.execute(
        "CREATE INDEX ix_credit_tx_task "
        "ON billing.credit_transactions (task_id) WHERE task_id IS NOT NULL;"
    )

    op.execute(
        "COMMENT ON TABLE billing.credit_transactions IS "
        "'Wave 0 SKELETON — full billing context lands Wave 2-3. "
        "Atomic 3-currency write partner to llm_gateway.llm_usage_log "
        "(llm-gateway invariant #7).';"
    )

    op.execute("ALTER TABLE billing.credit_transactions ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE billing.credit_transactions FORCE  ROW LEVEL SECURITY;")
    # Security audit H-1, 2026-05-19: use _shared.current_cell_id() helper
    # (returns NULL on empty/invalid GUC ⇒ default-deny). Inline current_setting
    # cast raises invalid_text_representation on empty GUC.
    op.execute(
        """
        CREATE POLICY ct_cell_isolation ON billing.credit_transactions
            USING (cell_id = _shared.current_cell_id());
        """
    )

    # Append-only ledger — paired with llm_usage_log per invariant #7. Architect-audit
    # H3 + Security audit best-practice, 2026-05-19.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION billing.deny_update_delete_credit_transactions()
        RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'billing.credit_transactions is append-only';
        END;
        $$;
        """
    )
    op.execute(
        """
        CREATE TRIGGER credit_transactions_no_update
            BEFORE UPDATE ON billing.credit_transactions
            FOR EACH STATEMENT EXECUTE FUNCTION
                billing.deny_update_delete_credit_transactions();
        """
    )
    op.execute(
        """
        CREATE TRIGGER credit_transactions_no_delete
            BEFORE DELETE ON billing.credit_transactions
            FOR EACH STATEMENT EXECUTE FUNCTION
                billing.deny_update_delete_credit_transactions();
        """
    )

    op.execute("GRANT SELECT, INSERT ON billing.credit_transactions TO oriion_app;")


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS credit_transactions_no_delete ON billing.credit_transactions;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS credit_transactions_no_update ON billing.credit_transactions;"
    )
    op.execute("DROP FUNCTION IF EXISTS billing.deny_update_delete_credit_transactions();")
    op.execute("DROP POLICY IF EXISTS ct_cell_isolation ON billing.credit_transactions;")
    op.execute("DROP TABLE IF EXISTS billing.credit_transactions;")
