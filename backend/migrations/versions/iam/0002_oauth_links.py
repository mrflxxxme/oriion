"""iam.oauth_links — external IdP linkages (DDL only in Wave 0).

DDL matches contracts/iam/schema.sql 1:1. Provider tokens stored encrypted
(AES-256-GCM, KMS-managed keys) per invariant 5. No Python code touches
this table in Wave 0; OAuth flow ships in Wave 1.

Revision ID: iam_0002_oauth_links
Down revision: iam_0001_users
"""

from __future__ import annotations

from alembic import op

revision: str = "iam_0002_oauth_links"
down_revision: str | None = "iam_0001_users"
branch_labels: tuple[str, ...] = ()
depends_on: str | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE iam.oauth_links (
            id                          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id                     uuid REFERENCES iam.users(id) ON DELETE SET NULL,
            provider                    text NOT NULL
                CHECK (provider IN ('yandex','google','vk','gitlab')),
            provider_user_id            text NOT NULL,
            access_token_encrypted      bytea,
            refresh_token_encrypted     bytea,
            expires_at                  timestamptz,
            created_at                  timestamptz NOT NULL DEFAULT now(),
            updated_at                  timestamptz NOT NULL DEFAULT now()
        );
        """
    )

    op.execute(
        """
        CREATE UNIQUE INDEX oauth_links_provider_uid_uidx
            ON iam.oauth_links (provider, provider_user_id);
        """
    )
    op.execute("CREATE INDEX oauth_links_user_id_idx ON iam.oauth_links (user_id);")

    op.execute(
        "COMMENT ON TABLE iam.oauth_links IS "
        "'External IdP linkages. Tokens encrypted AES-256-GCM with KMS-managed keys.';"
    )
    op.execute(
        "COMMENT ON COLUMN iam.oauth_links.access_token_encrypted IS "
        "'Ciphertext only. Plaintext MUST NOT be logged or persisted.';"
    )

    op.execute(
        """
        CREATE TRIGGER oauth_links_set_updated_at
            BEFORE UPDATE ON iam.oauth_links
            FOR EACH ROW EXECUTE FUNCTION _shared.set_updated_at();
        """
    )

    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON iam.oauth_links TO oriion_app;")


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS oauth_links_set_updated_at ON iam.oauth_links;")
    op.execute("DROP TABLE IF EXISTS iam.oauth_links;")
