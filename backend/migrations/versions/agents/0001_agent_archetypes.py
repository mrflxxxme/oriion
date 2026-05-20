"""agents.agent_archetypes — vertical-level AI personas.

DDL matches contracts/agents/schema.sql 1:1 (authoritative per ADR-024 §2 +
P-AUDIT-2 naming enforcement).

Revision ID: agents_0001_agent_archetypes
Down revision: _shared_0002_current_user_id_helper
Branch label: agents

Phase 00.5b Commit 5.
"""

from __future__ import annotations

from alembic import op

revision: str = "agents_0001_agent_archetypes"
down_revision: str | None = "_shared_0002_current_user_id_helper"
branch_labels: tuple[str, ...] = ("agents",)
depends_on: str | None = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS agents;")
    op.execute(
        """
        CREATE TABLE agents.agent_archetypes (
            id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            slug                  text NOT NULL,
            vertical_slug         text NOT NULL,
            display_name          text NOT NULL,
            role_category         text NOT NULL CHECK (role_category IN
                                    ('coordinator','researcher','writer','analyzer','validator','communicator')),
            prompt_version        text NOT NULL,
            model_provider_slug   text NOT NULL,
            model_name            text NOT NULL,
            model_fallback        text NULL,
            tools_allowed         text[] NOT NULL DEFAULT '{}',
            is_active             boolean NOT NULL DEFAULT true,
            status                text NOT NULL DEFAULT 'draft' CHECK (status IN
                                    ('draft','reviewed','promoted','locked')),
            created_at            timestamptz NOT NULL DEFAULT now(),
            updated_at            timestamptz NOT NULL DEFAULT now(),
            deprecated_at         timestamptz NULL,
            CONSTRAINT agent_archetypes_unique UNIQUE (vertical_slug, slug, prompt_version)
        );
        """
    )
    op.execute(
        """
        CREATE INDEX idx_agent_archetypes_vertical_active
            ON agents.agent_archetypes (vertical_slug)
            WHERE is_active = true AND deprecated_at IS NULL;
        """
    )
    op.execute(
        """
        CREATE INDEX idx_agent_archetypes_status
            ON agents.agent_archetypes (status, vertical_slug);
        """
    )
    op.execute("GRANT USAGE ON SCHEMA agents TO oriion_app;")
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON agents.agent_archetypes TO oriion_app;"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS agents.agent_archetypes;")
    op.execute("DROP SCHEMA IF EXISTS agents;")
