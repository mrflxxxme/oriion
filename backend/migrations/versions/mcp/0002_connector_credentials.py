"""mcp.connector_credentials — KMS-encrypted per-workspace connector credential store.

Phase 01.9b connector security core (PASS A). **PURE-CREATE**: a brand-new table
plus its own workspace-scoped RLS from scratch — ZERO ALTER/DROP of any existing
object (mcp.mcp_connections and every other table are untouched).

Custody model mirrors ``llm_gateway/0002_byok_keys`` (AES-256-GCM ciphertext only,
no plaintext) and the RLS shape of ``mcp/0001_mcp_connections`` (workspace
isolation via the ``_shared.current_workspace_id()`` GUC helper — missing/invalid
GUC → NULL → policy FALSE → default-deny). Only the ciphertext + a public-safe
sha256[:8] fingerprint are stored; the plaintext connector secret is discarded
after encryption by ``services.connector_credential_service``.

The RLS policy is hand-rolled with literal ``op.execute(...)`` SQL (no f-string
loops) so the security surface stays inspectable in the migration diff.

Revision ID: mcp_0002_connector_credentials
Down revision: mcp_0001_mcp_connections
Branch label: mcp (continued)
Depends on:    multitenancy_0001_workspaces (cross-schema FK)
"""

from __future__ import annotations

from alembic import op

revision: str = "mcp_0002_connector_credentials"
down_revision: str | None = "mcp_0001_mcp_connections"
branch_labels: tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = "multitenancy_0001_workspaces"


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE mcp.connector_credentials (
            id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id      uuid NOT NULL
                REFERENCES multitenancy.workspaces(id) ON DELETE CASCADE,
            connector_slug    text NOT NULL
                CHECK (connector_slug IN ('telegram-bot','yandex-disk','imap-smtp')),
            cred_encrypted    bytea NOT NULL,
            cred_fingerprint  text NOT NULL,
            label             text NOT NULL,
            is_active         boolean NOT NULL DEFAULT true,
            created_by        uuid NOT NULL,
            created_at        timestamptz NOT NULL DEFAULT now(),
            updated_at        timestamptz NOT NULL DEFAULT now(),
            revoked_at        timestamptz NULL,
            CONSTRAINT connector_credentials_unique_label
                UNIQUE (workspace_id, connector_slug, label)
        );
        """
    )

    # Partial index for the owner-config "active credentials" listing path.
    op.execute(
        """
        CREATE INDEX connector_credentials_workspace_active_idx
            ON mcp.connector_credentials (workspace_id)
            WHERE is_active = true AND revoked_at IS NULL;
        """
    )

    op.execute(
        "COMMENT ON TABLE mcp.connector_credentials IS "
        "'KMS-encrypted per-workspace connector credential custody (Phase 01.9b). "
        "Workspace-scoped RLS; ciphertext + a public-safe 8-hex sha256 fingerprint "
        "only — no plaintext.';"
    )
    op.execute(
        "COMMENT ON COLUMN mcp.connector_credentials.cred_encrypted IS "
        "'AES-256-GCM ciphertext (nonce || ct || tag) via get_kms_provider(). "
        "The plaintext connector secret is never stored.';"
    )
    op.execute(
        "COMMENT ON COLUMN mcp.connector_credentials.cred_fingerprint IS "
        "'Public-safe sha256(plaintext) truncated to the first 8 hex chars — "
        "surfaced in API responses; not reversible.';"
    )

    op.execute(
        """
        CREATE TRIGGER connector_credentials_set_updated_at
            BEFORE UPDATE ON mcp.connector_credentials
            FOR EACH ROW EXECUTE FUNCTION _shared.set_updated_at();
        """
    )

    # RLS — workspace_id isolation via _shared.current_workspace_id() GUC.
    # Missing/invalid GUC → NULL → policy evaluates FALSE → default-deny.
    op.execute("ALTER TABLE mcp.connector_credentials ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE mcp.connector_credentials FORCE  ROW LEVEL SECURITY;")
    op.execute(
        """
        CREATE POLICY connector_credentials_workspace_isolation
            ON mcp.connector_credentials
            USING (workspace_id = _shared.current_workspace_id());
        """
    )

    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON mcp.connector_credentials TO oriion_app;")


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS connector_credentials_workspace_isolation "
        "ON mcp.connector_credentials;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS connector_credentials_set_updated_at "
        "ON mcp.connector_credentials;"
    )
    op.execute("DROP TABLE IF EXISTS mcp.connector_credentials;")
