"""iam.totp_credentials + totp_backup_codes + magic_link_tokens (Phase 01.8).

DDL matches contracts/iam/schema.sql 1:1. Greenfield pure-CREATE — three new
user-scoped auth tables for the 01.8 auth extensions:

  * totp_credentials  — per-user RFC-6238 second factor. The shared secret is
    stored ENCRYPTED AT REST (``secret_encrypted bytea``, AES-256-GCM via the
    KMS provider); never plaintext, never logged.
  * totp_backup_codes — single-use recovery codes, SHA-256 hashed (token idiom).
  * magic_link_tokens — single-use passwordless-login tokens, SHA-256 hashed
    (copies the email_verification_tokens pattern: hash at rest, expiry,
    single-use).

These are user-scoped (keyed on user_id / credential_id, NOT cell_id) — exactly
like iam.sessions / email_verification_tokens / password_reset_tokens — so they
carry NO cell RLS policy, only a GRANT to oriion_app. The updated_at trigger on
totp_credentials uses the literal _rls.updated_at_trigger helper (f-string-free
migration body → tripwire recognizes pure-CREATE).

Revision ID: iam_0007_totp_and_magic_link
Down revision: iam_0006_password_reset_tokens
"""

from __future__ import annotations

from alembic import op

from migrations._rls import updated_at_trigger

revision: str = "iam_0007_totp_and_magic_link"
down_revision: str | None = "iam_0006_password_reset_tokens"
branch_labels: tuple[str, ...] = ()
depends_on: str | None = None


def upgrade() -> None:
    # ── iam.totp_credentials ───────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE iam.totp_credentials (
            id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id             uuid NOT NULL REFERENCES iam.users(id) ON DELETE CASCADE,
            secret_encrypted    bytea NOT NULL,
            confirmed_at        timestamptz,
            disabled_at         timestamptz,
            created_at          timestamptz NOT NULL DEFAULT now(),
            updated_at          timestamptz NOT NULL DEFAULT now()
        );
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX totp_credentials_user_id_uidx
            ON iam.totp_credentials (user_id);
        """
    )
    op.execute(
        """
        CREATE INDEX totp_credentials_active_idx
            ON iam.totp_credentials (user_id)
            WHERE confirmed_at IS NOT NULL AND disabled_at IS NULL;
        """
    )
    op.execute(
        "COMMENT ON TABLE iam.totp_credentials IS "
        "'Per-user TOTP second factor. secret_encrypted is an AES-256-GCM blob "
        "(KMS); never stored/logged in plaintext. Active when confirmed_at IS NOT "
        "NULL AND disabled_at IS NULL.';"
    )
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON iam.totp_credentials TO oriion_app;")
    updated_at_trigger("iam.totp_credentials")

    # ── iam.totp_backup_codes ──────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE iam.totp_backup_codes (
            id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            credential_id   uuid NOT NULL
                                REFERENCES iam.totp_credentials(id) ON DELETE CASCADE,
            code_hash       text NOT NULL,
            used_at         timestamptz,
            created_at      timestamptz NOT NULL DEFAULT now()
        );
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX totp_backup_codes_hash_uidx
            ON iam.totp_backup_codes (code_hash);
        """
    )
    op.execute(
        """
        CREATE INDEX totp_backup_codes_cred_active_idx
            ON iam.totp_backup_codes (credential_id)
            WHERE used_at IS NULL;
        """
    )
    op.execute(
        "COMMENT ON TABLE iam.totp_backup_codes IS "
        "'Single-use TOTP recovery codes. SHA-256 hashed before storage; "
        "consumed at most once (used_at).';"
    )
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON iam.totp_backup_codes TO oriion_app;")

    # ── iam.magic_link_tokens ──────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE iam.magic_link_tokens (
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
        CREATE UNIQUE INDEX magic_link_tokens_hash_uidx
            ON iam.magic_link_tokens (token_hash);
        """
    )
    op.execute(
        """
        CREATE INDEX magic_link_tokens_user_active_idx
            ON iam.magic_link_tokens (user_id, expires_at)
            WHERE used_at IS NULL;
        """
    )
    op.execute(
        "COMMENT ON TABLE iam.magic_link_tokens IS "
        "'Single-use passwordless-login tokens. SHA-256 hashed before storage; "
        "plaintext only over email.';"
    )
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON iam.magic_link_tokens TO oriion_app;")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS iam.magic_link_tokens;")
    op.execute("DROP TABLE IF EXISTS iam.totp_backup_codes;")
    op.execute("DROP TABLE IF EXISTS iam.totp_credentials;")
