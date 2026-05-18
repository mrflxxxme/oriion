"""iam.sessions + iam.refresh_tokens — login sessions + OWASP rotation chain.

DDL matches contracts/iam/schema.sql 1:1. Invariant 3: refresh tokens are
single-use; reuse of a used token revokes the entire rotation_chain_id
and emits oriion.iam.session.revoked.v1 with reason=security_incident.

Revision ID: iam_0004_sessions_refresh_tokens
Down revision: iam_0003_consents
"""

from __future__ import annotations

from alembic import op

revision: str = "iam_0004_sessions_refresh_tokens"
down_revision: str | None = "iam_0003_consents"
branch_labels: tuple[str, ...] = ()
depends_on: str | None = None


def upgrade() -> None:
    # ── iam.sessions ───────────────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE iam.sessions (
            id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id         uuid NOT NULL REFERENCES iam.users(id) ON DELETE CASCADE,
            ip_address      inet,
            user_agent      text,
            fingerprint     text,
            last_seen_at    timestamptz NOT NULL DEFAULT now(),
            expires_at      timestamptz NOT NULL,
            revoked_at      timestamptz,
            created_at      timestamptz NOT NULL DEFAULT now()
        );
        """
    )

    op.execute("CREATE INDEX sessions_user_id_idx ON iam.sessions (user_id);")
    op.execute("CREATE INDEX sessions_expires_at_idx ON iam.sessions (expires_at);")
    op.execute(
        """
        CREATE INDEX sessions_active_idx
            ON iam.sessions (user_id, expires_at)
            WHERE revoked_at IS NULL;
        """
    )

    op.execute(
        "COMMENT ON TABLE iam.sessions IS "
        "'Active login sessions per user. ON DELETE CASCADE from users.';"
    )

    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON iam.sessions TO oriion_app;")

    # ── iam.refresh_tokens ─────────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE iam.refresh_tokens (
            id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            session_id          uuid NOT NULL REFERENCES iam.sessions(id) ON DELETE CASCADE,
            token_hash          text NOT NULL,
            rotated_to          uuid REFERENCES iam.refresh_tokens(id) ON DELETE SET NULL,
            rotation_chain_id   uuid NOT NULL,
            issued_at           timestamptz NOT NULL DEFAULT now(),
            expires_at          timestamptz NOT NULL,
            used_at             timestamptz,
            revoked_at          timestamptz
        );
        """
    )

    op.execute(
        "CREATE UNIQUE INDEX refresh_tokens_hash_uidx ON iam.refresh_tokens (token_hash);"
    )
    op.execute(
        "CREATE INDEX refresh_tokens_session_id_idx ON iam.refresh_tokens (session_id);"
    )
    op.execute(
        "CREATE INDEX refresh_tokens_chain_idx ON iam.refresh_tokens (rotation_chain_id);"
    )
    op.execute(
        """
        CREATE INDEX refresh_tokens_active_idx
            ON iam.refresh_tokens (session_id, expires_at)
            WHERE used_at IS NULL AND revoked_at IS NULL;
        """
    )

    op.execute(
        "COMMENT ON TABLE iam.refresh_tokens IS "
        "'Single-use refresh tokens. Reuse of a used token revokes the entire "
        "rotation_chain_id.';"
    )

    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON iam.refresh_tokens TO oriion_app;"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS iam.refresh_tokens;")
    op.execute("DROP TABLE IF EXISTS iam.sessions;")
