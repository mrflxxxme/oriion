"""llm_gateway.llm_usage_log — append-only per-request audit log.

DDL matches contracts/llm-gateway/schema.sql 1:1 (authoritative per ADR-024).
Three money columns per ADR-018 amendment 2026-05-19 (RU billing):

    cost_usd            — provider native (invoice reconciliation source)
    cost_rub            — customer-facing settlement (matches credit_transactions)
    fx_rate_usd_to_rub  — pinned snapshot at request time

All three NOT NULL DEFAULT 0 — service layer is responsible for the atomic write.

Revision ID: llm_gateway_0003_llm_usage_log
Down revision: llm_gateway_0002_byok_keys
"""

from __future__ import annotations

from alembic import op

revision: str = "llm_gateway_0003_llm_usage_log"
down_revision: str | None = "llm_gateway_0002_byok_keys"
branch_labels: tuple[str, ...] | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE llm_gateway.llm_usage_log (
            id                    bigserial PRIMARY KEY,
            workspace_id          uuid NOT NULL,
            cell_id               uuid NOT NULL,
            task_id               uuid NULL,
            byok_key_id           uuid NULL
                REFERENCES llm_gateway.byok_keys(id),
            provider_slug         text NOT NULL,
            model_name            text NOT NULL,
            request_id            text NOT NULL,
            input_tokens          int  NOT NULL DEFAULT 0,
            output_tokens         int  NOT NULL DEFAULT 0,
            cached_input_tokens   int  NOT NULL DEFAULT 0,
            cost_usd              numeric(10,6) NOT NULL DEFAULT 0,
            cost_rub              numeric(12,4) NOT NULL DEFAULT 0,
            fx_rate_usd_to_rub    numeric(10,6) NOT NULL DEFAULT 0,
            latency_ms            int  NOT NULL DEFAULT 0,
            status                text NOT NULL
                CHECK (status IN ('success','error','timeout','rate_limited')),
            error_code            text NULL,
            created_at            timestamptz NOT NULL DEFAULT now()
        );
        """
    )

    op.execute(
        "CREATE INDEX idx_llm_usage_log_workspace_time "
        "ON llm_gateway.llm_usage_log (workspace_id, created_at DESC);"
    )
    op.execute(
        "CREATE INDEX idx_llm_usage_log_byok_time "
        "ON llm_gateway.llm_usage_log (byok_key_id, created_at DESC) "
        "WHERE byok_key_id IS NOT NULL;"
    )
    op.execute(
        "CREATE INDEX idx_llm_usage_log_cell_time "
        "ON llm_gateway.llm_usage_log (cell_id, created_at DESC);"
    )
    op.execute(
        "CREATE INDEX idx_llm_usage_log_task "
        "ON llm_gateway.llm_usage_log (task_id) WHERE task_id IS NOT NULL;"
    )
    op.execute(
        "CREATE INDEX idx_llm_usage_log_provider_time "
        "ON llm_gateway.llm_usage_log (provider_slug, created_at DESC);"
    )

    op.execute(
        "COMMENT ON TABLE llm_gateway.llm_usage_log IS "
        "'Append-only LLM call audit. Cost-policy enforcement is upstream "
        "(cost-budget.yaml).';"
    )
    op.execute(
        "COMMENT ON COLUMN llm_gateway.llm_usage_log.cost_usd IS "
        "'TECHNICAL per-call cost from provider response (native USD). "
        "Not a policy threshold.';"
    )
    op.execute(
        "COMMENT ON COLUMN llm_gateway.llm_usage_log.cost_rub IS "
        "'Customer-facing settlement cost in RUB. cost_rub = cost_usd * fx_rate "
        "(atomic write).';"
    )
    op.execute(
        "COMMENT ON COLUMN llm_gateway.llm_usage_log.fx_rate_usd_to_rub IS "
        "'FX snapshot pinned at request-time (Wave 0: env-driven constant; "
        "Wave 1+: live FX feed).';"
    )

    op.execute("ALTER TABLE llm_gateway.llm_usage_log ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE llm_gateway.llm_usage_log FORCE  ROW LEVEL SECURITY;")
    op.execute(
        """
        CREATE POLICY llm_usage_log_workspace_isolation ON llm_gateway.llm_usage_log
            USING (
                workspace_id = current_setting('app.current_workspace_id', true)::uuid
            );
        """
    )

    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE " "ON llm_gateway.llm_usage_log TO oriion_app;"
    )
    op.execute("GRANT USAGE, SELECT ON SEQUENCE llm_gateway.llm_usage_log_id_seq TO oriion_app;")


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS llm_usage_log_workspace_isolation " "ON llm_gateway.llm_usage_log;"
    )
    op.execute("DROP TABLE IF EXISTS llm_gateway.llm_usage_log;")
