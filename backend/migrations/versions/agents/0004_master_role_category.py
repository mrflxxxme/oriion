"""agents.agent_archetypes — add 'master' to the role_category CHECK.

AC-W1-3 fast-follow (ADR-029): Phase 01.2 seeded the vertical Master archetype
with role_category='coordinator' because the CHECK lacked 'master'. This adds
'master' to the allow-list and re-points any existing Master rows to it, so the
category matches the role semantically.

The original CHECK was created INLINE/unnamed in agents_0001 → Postgres
auto-named it ``agent_archetypes_role_category_check``. The SQLAlchemy model
declares ``agent_archetypes_role_category_chk``. We drop both names defensively
and re-add the constraint with the model's declared name (aligning DB + model).

Revision ID: agents_0004_master_role_category
Down revision: agents_0003_agent_instances
"""

from __future__ import annotations

from alembic import op

revision: str = "agents_0004_master_role_category"
down_revision: str | None = "agents_0003_agent_instances"
branch_labels: tuple[str, ...] | None = None
depends_on: str | None = None

_WITH_MASTER = (
    "('coordinator','researcher','writer','analyzer','validator','communicator','master')"
)
_WITHOUT_MASTER = "('coordinator','researcher','writer','analyzer','validator','communicator')"


def upgrade() -> None:
    op.execute(
        "ALTER TABLE agents.agent_archetypes "
        "DROP CONSTRAINT IF EXISTS agent_archetypes_role_category_check;"
    )
    op.execute(
        "ALTER TABLE agents.agent_archetypes "
        "DROP CONSTRAINT IF EXISTS agent_archetypes_role_category_chk;"
    )
    op.execute(
        "ALTER TABLE agents.agent_archetypes "
        "ADD CONSTRAINT agent_archetypes_role_category_chk "
        f"CHECK (role_category IN {_WITH_MASTER});"
    )
    # Re-point existing Master archetypes seeded under the reuse-hack.
    op.execute(
        "UPDATE agents.agent_archetypes SET role_category = 'master' "
        "WHERE slug = 'master' AND role_category = 'coordinator';"
    )


def downgrade() -> None:
    # Revert Master rows BEFORE re-adding the narrower CHECK so it validates.
    op.execute(
        "UPDATE agents.agent_archetypes SET role_category = 'coordinator' "
        "WHERE slug = 'master' AND role_category = 'master';"
    )
    op.execute(
        "ALTER TABLE agents.agent_archetypes "
        "DROP CONSTRAINT IF EXISTS agent_archetypes_role_category_chk;"
    )
    op.execute(
        "ALTER TABLE agents.agent_archetypes "
        "ADD CONSTRAINT agent_archetypes_role_category_chk "
        f"CHECK (role_category IN {_WITHOUT_MASTER});"
    )
