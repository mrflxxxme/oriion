"""iam.password_reset_tokens — single-use reset with chain-revoke.

DDL matches contracts/iam/schema.sql 1:1. Invariant 8: single-use, 1h TTL,
SHA-256 hashed; reuse of a consumed token revokes the entire reset_chain_id
AND every active session for the user (emit oriion.iam.session.revoked.v1
with reason=security_incident).

Revision ID: iam_0006_password_reset_tokens
Down revision: iam_0005_email_verification_tokens
"""

from __future__ import annotations

from alembic import op

revision: str = "iam_0006_password_reset_tokens"
down_revision: str | None = "iam_0005_email_verification_tokens"
branch_labels: tuple[str, ...] = ()
depends_on: str | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE iam.password_reset_tokens (
            id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id             uuid NOT NULL REFERENCES iam.users(id) ON DELETE CASCADE,
            token_hash          text NOT NULL,
            reset_chain_id      uuid NOT NULL,
            expires_at          timestamptz NOT NULL,
            used_at             timestamptz,
            revoked_at          timestamptz,
            created_at          timestamptz NOT NULL DEFAULT now()
        );
        """
    )

    op.execute(
        """
        CREATE UNIQUE INDEX password_reset_tokens_hash_uidx
            ON iam.password_reset_tokens (token_hash);
        """
    )
    op.execute(
        "CREATE INDEX password_reset_tokens_user_id_idx " "ON iam.password_reset_tokens (user_id);"
    )
    op.execute(
        "CREATE INDEX password_reset_tokens_chain_idx "
        "ON iam.password_reset_tokens (reset_chain_id);"
    )
    op.execute(
        """
        CREATE INDEX password_reset_tokens_user_active_idx
            ON iam.password_reset_tokens (user_id, expires_at)
            WHERE used_at IS NULL AND revoked_at IS NULL;
        """
    )

    op.execute(
        "COMMENT ON TABLE iam.password_reset_tokens IS "
        "'Single-use password-reset tokens. Reuse of a used token revokes the "
        "entire reset_chain_id.';"
    )

    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON iam.password_reset_tokens " "TO oriion_app;"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS iam.password_reset_tokens;")
