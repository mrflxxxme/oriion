"""rbac.role_permissions — many-to-many bridge between roles and permissions.

DDL matches contracts/rbac/schema.sql 1:1 (authoritative per ADR-024).

Revision ID: rbac_0003_role_permissions
Down revision: rbac_0002_permissions
Branch label: rbac (continued)
"""

from __future__ import annotations

from alembic import op

revision: str = "rbac_0003_role_permissions"
down_revision: str | None = "rbac_0002_permissions"
branch_labels: tuple[str, ...] | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE rbac.role_permissions (
            role_id        uuid NOT NULL
                REFERENCES rbac.system_roles(id) ON DELETE CASCADE,
            permission_id  uuid NOT NULL
                REFERENCES rbac.permissions(id)  ON DELETE RESTRICT,
            granted_at     timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (role_id, permission_id)
        );
        """
    )

    op.execute(
        "CREATE INDEX role_permissions_permission_id_idx "
        "ON rbac.role_permissions (permission_id);"
    )

    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON rbac.role_permissions TO oriion_app;")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS rbac.role_permissions;")
