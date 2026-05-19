"""rbac.system_roles — built-in role catalogue.

DDL matches contracts/rbac/schema.sql 1:1 (authoritative per ADR-024).
Slugs are stable identifiers used by API + client code. is_built_in=true
rows are immutable (enforced at the application layer; DB does not protect).

Revision ID: rbac_0001_system_roles
Down revision: _shared_0002_current_user_id_helper
Branch label: rbac
"""

from __future__ import annotations

from alembic import op

revision: str = "rbac_0001_system_roles"
down_revision: str | None = "_shared_0002_current_user_id_helper"
branch_labels: tuple[str, ...] = ("rbac",)
depends_on: str | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE rbac.system_roles (
            id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            slug          text NOT NULL UNIQUE,
            display_name  text NOT NULL,
            description   text,
            is_built_in   boolean NOT NULL DEFAULT true,
            created_at    timestamptz NOT NULL DEFAULT now(),
            updated_at    timestamptz NOT NULL DEFAULT now()
        );
        """
    )

    op.execute(
        "COMMENT ON TABLE rbac.system_roles IS "
        "'System-level roles. NOT to be confused with agents.agent_archetypes "
        "(AI personas).';"
    )

    op.execute(
        """
        CREATE TRIGGER system_roles_set_updated_at
            BEFORE UPDATE ON rbac.system_roles
            FOR EACH ROW EXECUTE FUNCTION _shared.set_updated_at();
        """
    )

    # Catalogue table — readable by all authenticated users. RLS disabled.
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON rbac.system_roles TO oriion_app;")


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS system_roles_set_updated_at ON rbac.system_roles;")
    op.execute("DROP TABLE IF EXISTS rbac.system_roles;")
