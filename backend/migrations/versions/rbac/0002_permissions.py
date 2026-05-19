"""rbac.permissions — granular permission catalogue.

DDL matches contracts/rbac/schema.sql 1:1 (authoritative per ADR-024).
Slug format strictly `<resource>.<action>` enforced via CHECK regex.

Revision ID: rbac_0002_permissions
Down revision: rbac_0001_system_roles
Branch label: rbac (continued)
"""

from __future__ import annotations

from alembic import op

revision: str = "rbac_0002_permissions"
down_revision: str | None = "rbac_0001_system_roles"
branch_labels: tuple[str, ...] | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute(
        r"""
        CREATE TABLE rbac.permissions (
            id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            slug          text NOT NULL UNIQUE
                CHECK (slug ~ '^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$'),
            display_name  text NOT NULL,
            description   text,
            category      text NOT NULL,
            created_at    timestamptz NOT NULL DEFAULT now()
        );
        """
    )

    op.execute("CREATE INDEX permissions_category_idx ON rbac.permissions (category);")

    op.execute(
        "COMMENT ON COLUMN rbac.permissions.slug IS "
        "'Format: <resource>.<action>. Lowercase; underscores allowed within segments.';"
    )

    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON rbac.permissions TO oriion_app;")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS rbac.permissions;")
