"""_shared.current_user_id() SQL helper used by multitenancy RLS policies.

Per ADR-009 amendment 2026-05-19 (3-GUC layered RLS model), `multitenancy.*`
policies key off ``_shared.current_user_id()`` (membership EXISTS pattern)
rather than embedding ``current_setting(...)::uuid`` inline. The helper
returns NULL on missing GUC, which makes every dependent policy evaluate
FALSE by default-deny.

Why a helper function instead of inline current_setting?
- Single point of change if Wave 1+ wants to add request-tracing hooks.
- Cleaner policy DDL (one identifier vs nested cast + missing_ok flag).
- Centralizes the missing-GUC → NULL contract in one place.

Revision IDs
------------
Revision ID: _shared_0002_current_user_id_helper
Down revision: _shared_0001_init
Branch label: _shared (continued)
Create date: 2026-05-19
"""

from __future__ import annotations

from alembic import op

revision: str = "_shared_0002_current_user_id_helper"
down_revision: str | None = "_shared_0001_init"
branch_labels: tuple[str, ...] | None = None
depends_on: str | None = None


def upgrade() -> None:
    # Returns NULL when the GUC is unset or invalid (default-deny posture).
    # CREATE OR REPLACE is idempotent — safe under re-run.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION _shared.current_user_id()
        RETURNS uuid
        LANGUAGE plpgsql
        STABLE
        AS $$
        DECLARE
            raw text;
        BEGIN
            raw := current_setting('app.current_user_id', true);
            IF raw IS NULL OR raw = '' THEN
                RETURN NULL;
            END IF;
            BEGIN
                RETURN raw::uuid;
            EXCEPTION WHEN invalid_text_representation THEN
                RETURN NULL;
            END;
        END;
        $$;
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION _shared.current_workspace_id()
        RETURNS uuid
        LANGUAGE plpgsql
        STABLE
        AS $$
        DECLARE
            raw text;
        BEGIN
            raw := current_setting('app.current_workspace_id', true);
            IF raw IS NULL OR raw = '' THEN
                RETURN NULL;
            END IF;
            BEGIN
                RETURN raw::uuid;
            EXCEPTION WHEN invalid_text_representation THEN
                RETURN NULL;
            END;
        END;
        $$;
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION _shared.current_cell_id()
        RETURNS uuid
        LANGUAGE plpgsql
        STABLE
        AS $$
        DECLARE
            raw text;
        BEGIN
            raw := current_setting('app.current_cell_id', true);
            IF raw IS NULL OR raw = '' THEN
                RETURN NULL;
            END IF;
            BEGIN
                RETURN raw::uuid;
            EXCEPTION WHEN invalid_text_representation THEN
                RETURN NULL;
            END;
        END;
        $$;
        """
    )

    # Grant EXECUTE to the oriion_app role (USAGE on _shared schema already
    # granted by 0001_init.py). RLS policies on other schemas call these
    # functions during planning, so the app role MUST be able to EXECUTE.
    op.execute(
        "GRANT EXECUTE ON FUNCTION "
        "_shared.current_user_id(), "
        "_shared.current_workspace_id(), "
        "_shared.current_cell_id() "
        "TO oriion_app;"
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS _shared.current_cell_id();")
    op.execute("DROP FUNCTION IF EXISTS _shared.current_workspace_id();")
    op.execute("DROP FUNCTION IF EXISTS _shared.current_user_id();")
