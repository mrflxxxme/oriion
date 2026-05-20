"""agents.team_presets — opinionated archetype compositions.

Phase 00.5b Commit 5.
"""

from __future__ import annotations

from alembic import op

revision: str = "agents_0002_team_presets"
down_revision: str | None = "agents_0001_agent_archetypes"
branch_labels: tuple[str, ...] | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE agents.team_presets (
            id                          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            vertical_slug               text NOT NULL,
            slug                        text NOT NULL,
            display_name                text NOT NULL,
            description                 text NOT NULL DEFAULT '',
            archetype_ids               uuid[] NOT NULL,
            default_workflow_dag_json   jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at                  timestamptz NOT NULL DEFAULT now(),
            updated_at                  timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT team_presets_unique UNIQUE (vertical_slug, slug)
        );
        """
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON agents.team_presets TO oriion_app;"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS agents.team_presets;")
