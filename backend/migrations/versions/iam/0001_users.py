"""iam.users — canonical person record.

DDL matches contracts/iam/schema.sql 1:1 (architect-PR authoritative source
per ADR-024). password_algo CHECK enforces argon2id-only invariant 2.
Soft-delete via deleted_at (FZ-152 / GDPR retention purge job in Wave 1+).

Revision ID: iam_0001_users
Down revision: _shared_0001_init
Branch label: iam
"""

from __future__ import annotations

from alembic import op

revision: str = "iam_0001_users"
down_revision: str | None = "_shared_0001_init"
branch_labels: tuple[str, ...] = ("iam",)
depends_on: str | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE iam.users (
            id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            email               citext NOT NULL,
            email_verified_at   timestamptz,
            password_hash       text,
            password_algo       text NOT NULL DEFAULT 'argon2id'
                CHECK (password_algo IN ('argon2id')),
            display_name        text,
            locale              text NOT NULL DEFAULT 'ru-RU',
            timezone            text NOT NULL DEFAULT 'Europe/Moscow',
            created_at          timestamptz NOT NULL DEFAULT now(),
            updated_at          timestamptz NOT NULL DEFAULT now(),
            deleted_at          timestamptz
        );
        """
    )

    op.execute(
        """
        CREATE UNIQUE INDEX users_email_active_uidx
            ON iam.users (email)
            WHERE deleted_at IS NULL;
        """
    )
    op.execute(
        """
        CREATE INDEX users_deleted_at_idx
            ON iam.users (deleted_at)
            WHERE deleted_at IS NOT NULL;
        """
    )
    op.execute("CREATE INDEX users_created_at_desc_idx ON iam.users (created_at DESC);")

    op.execute(
        "COMMENT ON TABLE iam.users IS "
        "'Canonical user identity. Soft-delete via deleted_at; hard purge by retention job.';"
    )
    op.execute(
        "COMMENT ON COLUMN iam.users.password_algo IS "
        "'Only argon2id allowed. md5/sha1/bcrypt-legacy MUST NOT be introduced.';"
    )

    # updated_at trigger via _shared.set_updated_at()
    op.execute(
        """
        CREATE TRIGGER users_set_updated_at
            BEFORE UPDATE ON iam.users
            FOR EACH ROW EXECUTE FUNCTION _shared.set_updated_at();
        """
    )

    # Table-level GRANTs to oriion_app (USAGE on schema already granted in _shared).
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON iam.users TO oriion_app;"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS users_set_updated_at ON iam.users;")
    op.execute("DROP TABLE IF EXISTS iam.users;")
