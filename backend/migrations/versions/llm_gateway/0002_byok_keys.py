"""llm_gateway.byok_keys — per-workspace BYOK key custody.

DDL matches contracts/llm-gateway/schema.sql 1:1.
Raw API key never stored — only AES-256-GCM ciphertext (nonce || ct || tag).
Per-workspace RLS + role-restriction (owner/admin/billing only).

Cross-schema FK to multitenancy.workspaces — depends_on enforced.

Revision ID: llm_gateway_0002_byok_keys
Down revision: llm_gateway_0001_llm_provider_config
Depends on:    multitenancy_0001_workspaces (cross-schema FK)
"""

from __future__ import annotations

from alembic import op

revision: str = "llm_gateway_0002_byok_keys"
down_revision: str | None = "llm_gateway_0001_llm_provider_config"
branch_labels: tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = "multitenancy_0001_workspaces"


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE llm_gateway.byok_keys (
            id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id          uuid NOT NULL
                REFERENCES multitenancy.workspaces(id) ON DELETE CASCADE,
            provider_slug         text NOT NULL
                REFERENCES llm_gateway.llm_provider_config(provider_slug),
            key_encrypted         bytea NOT NULL,
            key_fingerprint       text NOT NULL,
            label                 text NOT NULL,
            monthly_quota_usd     numeric(12,4) NULL,
            monthly_used_usd      numeric(12,4) NOT NULL DEFAULT 0,
            is_active             boolean NOT NULL DEFAULT true,
            created_by            uuid NOT NULL,
            created_at            timestamptz NOT NULL DEFAULT now(),
            updated_at            timestamptz NOT NULL DEFAULT now(),
            revoked_at            timestamptz NULL,
            CONSTRAINT byok_keys_unique_label
                UNIQUE (workspace_id, provider_slug, label)
        );
        """
    )

    op.execute(
        """
        CREATE INDEX idx_byok_keys_workspace_active
            ON llm_gateway.byok_keys (workspace_id)
            WHERE is_active = true AND revoked_at IS NULL;
        """
    )

    op.execute(
        "COMMENT ON COLUMN llm_gateway.byok_keys.monthly_quota_usd IS "
        "'TECHNICAL soft-quota (provider-side, USD). Best-effort warning at "
        "80%/100%. NOT a policy cap — policy is in cost-budget.yaml (P-AUDIT-1).';"
    )
    op.execute(
        "COMMENT ON COLUMN llm_gateway.byok_keys.key_encrypted IS "
        "'AES-256-GCM ciphertext. DEK is per-workspace, wrapped by platform KMS "
        "(Wave 0: LocalAESKMS; Wave 1+: Yandex KMS).';"
    )

    op.execute(
        """
        CREATE TRIGGER byok_keys_set_updated_at
            BEFORE UPDATE ON llm_gateway.byok_keys
            FOR EACH ROW EXECUTE FUNCTION _shared.set_updated_at();
        """
    )

    # RLS — workspace_id isolation + role restriction (owner/admin/billing only).
    op.execute("ALTER TABLE llm_gateway.byok_keys ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE llm_gateway.byok_keys FORCE  ROW LEVEL SECURITY;")

    op.execute(
        """
        CREATE POLICY byok_keys_workspace_isolation ON llm_gateway.byok_keys
            USING (
                workspace_id = current_setting('app.current_workspace_id', true)::uuid
            );
        """
    )

    op.execute(
        """
        CREATE POLICY byok_keys_role_restriction ON llm_gateway.byok_keys
            FOR ALL
            USING (
                current_setting('app.current_role_slug', true)
                    IN ('owner', 'admin', 'billing')
            );
        """
    )

    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE " "ON llm_gateway.byok_keys TO oriion_app;")


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS byok_keys_role_restriction ON llm_gateway.byok_keys;")
    op.execute("DROP POLICY IF EXISTS byok_keys_workspace_isolation ON llm_gateway.byok_keys;")
    op.execute("DROP TRIGGER IF EXISTS byok_keys_set_updated_at ON llm_gateway.byok_keys;")
    op.execute("DROP TABLE IF EXISTS llm_gateway.byok_keys;")
