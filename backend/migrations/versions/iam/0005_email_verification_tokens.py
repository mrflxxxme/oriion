"""iam.email_verification_tokens — single-use email-ownership proofs.

DDL matches contracts/iam/schema.sql 1:1. Invariant 7: single-use, 24h TTL,
SHA-256 hashed; plaintext goes only over email. Re-requesting a token revokes
any prior unused tokens for the same user.

Revision ID: iam_0005_email_verification_tokens
Down revision: iam_0004_sessions_refresh_tokens
"""

from __future__ import annotations

from alembic import op

revision: str = "iam_0005_email_verification_tokens"
down_revision: str | None = "iam_0004_sessions_refresh_tokens"
branch_labels: tuple[str, ...] = ()
depends_on: str | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE iam.email_verification_tokens (
            id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id         uuid NOT NULL REFERENCES iam.users(id) ON DELETE CASCADE,
            token_hash      text NOT NULL,
            expires_at      timestamptz NOT NULL,
            used_at         timestamptz,
            created_at      timestamptz NOT NULL DEFAULT now()
        );
        """
    )

    op.execute(
        """
        CREATE UNIQUE INDEX email_verification_tokens_hash_uidx
            ON iam.email_verification_tokens (token_hash);
        """
    )
    op.execute(
        """
        CREATE INDEX email_verification_tokens_user_active_idx
            ON iam.email_verification_tokens (user_id, expires_at)
            WHERE used_at IS NULL;
        """
    )

    op.execute(
        "COMMENT ON TABLE iam.email_verification_tokens IS "
        "'Single-use email-verification tokens. SHA-256 hashed before storage; "
        "plaintext only over email.';"
    )

    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON iam.email_verification_tokens "
        "TO oriion_app;"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS iam.email_verification_tokens;")
