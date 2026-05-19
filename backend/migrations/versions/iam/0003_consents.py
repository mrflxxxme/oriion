"""iam.consents — FZ-152 / GDPR consent ledger.

DDL matches contracts/iam/schema.sql 1:1. Invariant 6: pdn consent
mandatory before register completes (enforced at service layer).
Version pinned at grant time; revocation is soft.

Revision ID: iam_0003_consents
Down revision: iam_0002_oauth_links
"""

from __future__ import annotations

from alembic import op

revision: str = "iam_0003_consents"
down_revision: str | None = "iam_0002_oauth_links"
branch_labels: tuple[str, ...] = ()
depends_on: str | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE iam.consents (
            id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id         uuid NOT NULL REFERENCES iam.users(id) ON DELETE CASCADE,
            kind            text NOT NULL
                CHECK (kind IN ('pdn','marketing','tos')),
            version         text NOT NULL,
            ip              inet,
            user_agent      text,
            granted_at      timestamptz NOT NULL DEFAULT now(),
            revoked_at      timestamptz
        );
        """
    )

    op.execute(
        """
        CREATE INDEX consents_user_kind_active_idx
            ON iam.consents (user_id, kind)
            WHERE revoked_at IS NULL;
        """
    )
    op.execute("CREATE INDEX consents_user_id_idx ON iam.consents (user_id);")

    op.execute(
        "COMMENT ON TABLE iam.consents IS "
        "'FZ-152 / GDPR consent ledger. pdn is mandatory before register; "
        "revocation is soft.';"
    )
    op.execute(
        "COMMENT ON COLUMN iam.consents.version IS "
        "'Privacy Policy / consent-form version pinned at grant time. Never mutated.';"
    )

    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON iam.consents TO oriion_app;")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS iam.consents;")
