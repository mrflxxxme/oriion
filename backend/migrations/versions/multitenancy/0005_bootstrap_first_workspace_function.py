"""multitenancy.bootstrap_first_workspace(...) — SECURITY DEFINER provisioner.

Per Phase 00.5 Topic 1 resolution (RLS Option A, 2026-05-20): the register()
bootstrap path cannot satisfy the FORCE-RLS-protected INSERT WITH CHECK
policies on multitenancy.{workspaces, cells, cell_members} under the
non-superuser `oriion_app` role, because the just-created user has no
`app.current_user_id` GUC set yet (chicken-and-egg: GUC requires user_id,
user_id requires registration).

This function mirrors the pattern of `multitenancy.provision_cell_schema`
(see migration 0004): SECURITY DEFINER so it executes with the migration
owner's privileges (which include BYPASSRLS), and EXECUTE granted to
`oriion_app`. The application calls it from a normal request-scoped TX
during register(); the entire bootstrap (workspace + cell + cell_member +
per-cell schema materialization) is atomic with the user-row INSERT done
by AuthService via the shared AsyncSession.

Audit closures:
  * Architecture H1 (PR #32 H-DEFER-2 carryover): register() writes to
    FORCE-RLS tables without GUC → now goes through SECURITY DEFINER func.
  * Architecture H2 (new pre-Phase-05 audit): set_tenant_context dead code
    → addressed by Commit 1 + middleware (see _shared/middleware/tenant_context.py).
  * Compliance H-1: ADR-014 "default-deny RLS" claim → now honest
    (ADR-014 amendment lands in same commit).

Idempotency:
  * Same `(user_id, workspace_slug)` re-invocation: function returns the
    existing IDs by slug lookup (matches workspace_service.provision_initial_workspace
    replay behaviour pre-refactor).

Revision ID: multitenancy_0005_bootstrap_first_workspace_function
Down revision: multitenancy_0004_provision_cell_schema_function
Branch label: multitenancy (continued)
"""

from __future__ import annotations

from alembic import op

revision: str = "multitenancy_0005_bootstrap_first_workspace_function"
down_revision: str | None = "multitenancy_0004_provision_cell_schema_function"
branch_labels: tuple[str, ...] | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute(
        r"""
        CREATE OR REPLACE FUNCTION multitenancy.bootstrap_first_workspace(
            p_user_id          uuid,
            p_workspace_slug   text,
            p_display_name     text
        )
        RETURNS TABLE(
            workspace_id  uuid,
            cell_id       uuid,
            schema_name   text,
            was_replay    boolean
        )
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $func$
        DECLARE
            v_workspace_id  uuid;
            v_cell_id       uuid;
            v_schema_name   text;
            v_was_replay    boolean := false;
        BEGIN
            IF p_user_id IS NULL THEN
                RAISE EXCEPTION 'p_user_id cannot be NULL';
            END IF;
            IF p_workspace_slug IS NULL OR length(p_workspace_slug) = 0 THEN
                RAISE EXCEPTION 'p_workspace_slug must be non-empty';
            END IF;
            IF p_display_name IS NULL OR length(p_display_name) = 0 THEN
                RAISE EXCEPTION 'p_display_name must be non-empty';
            END IF;

            -- Idempotent replay path: existing active workspace with this slug
            -- + its default cell. Mirrors the pre-refactor workspace_service
            -- replay logic so registrant-collision behavior is unchanged.
            SELECT w.id INTO v_workspace_id
            FROM multitenancy.workspaces w
            WHERE w.slug = p_workspace_slug
              AND w.deleted_at IS NULL
            LIMIT 1;

            IF v_workspace_id IS NOT NULL THEN
                SELECT c.id INTO v_cell_id
                FROM multitenancy.cells c
                WHERE c.workspace_id = v_workspace_id
                  AND c.slug = 'default'
                LIMIT 1;

                IF v_cell_id IS NOT NULL THEN
                    v_was_replay := true;
                    v_schema_name := 'cell_' || replace(v_cell_id::text, '-', '_');
                    RETURN QUERY SELECT v_workspace_id, v_cell_id, v_schema_name, v_was_replay;
                    RETURN;
                END IF;
            END IF;

            -- Fresh INSERT path. SECURITY DEFINER lets us bypass the
            -- workspaces_write_insert_with_context / cells_write_insert_with_context /
            -- cell_members_write_insert_with_context policies which require
            -- `_shared.current_user_id()` IS NOT NULL — at register-time the
            -- GUC is unset because the user has no session yet.
            INSERT INTO multitenancy.workspaces (slug, display_name, plan_tier)
            VALUES (p_workspace_slug, p_display_name, 'free')
            RETURNING id INTO v_workspace_id;

            INSERT INTO multitenancy.cells (workspace_id, slug, display_name)
            VALUES (v_workspace_id, 'default', 'Default cell')
            RETURNING id INTO v_cell_id;

            -- Add the registrant as a cell_member. The role_id is the
            -- well-known "system.owner" UUID seeded by rbac/0005_seed_built_in_roles.
            -- We look it up by code so the seed identifier is the source of
            -- truth, not a hardcoded UUID.
            INSERT INTO multitenancy.cell_members (cell_id, user_id, role_id, invited_by)
            SELECT v_cell_id, p_user_id, sr.id, p_user_id
            FROM rbac.system_roles sr
            WHERE sr.code = 'cell.owner'
            LIMIT 1;

            -- Per-cell schema materialization (delegates to provision_cell_schema
            -- which is itself SECURITY DEFINER — composition of privileged ops).
            SELECT multitenancy.provision_cell_schema(v_cell_id) INTO v_schema_name;

            RETURN QUERY SELECT v_workspace_id, v_cell_id, v_schema_name, v_was_replay;
        END;
        $func$;
        """
    )

    op.execute(
        "GRANT EXECUTE ON FUNCTION multitenancy.bootstrap_first_workspace(uuid, text, text) "
        "TO oriion_app;"
    )

    op.execute(
        "COMMENT ON FUNCTION multitenancy.bootstrap_first_workspace(uuid, text, text) IS "
        "'Register-time bootstrap escape for the 3-GUC RLS posture. "
        "SECURITY DEFINER so the app role can provision the first workspace + "
        "cell + cell_member + per-cell schema for a freshly-created user whose "
        "tenant GUCs are not yet set. Idempotent on slug lookup. "
        "Per Phase 00.5 Topic 1 / ADR-014 amendment 2026-05-20.';"
    )

    # ── companion: resolve_user_first_membership ─────────────────────────
    # Phase 00.5 Architecture H2 closure — the tenant_context middleware
    # needs to look up (workspace_id, cell_id) for an authenticated user
    # BEFORE the 3-GUC can be set. cell_members.cell_members_select_self_row
    # requires the GUC, so the lookup hits default-deny without a helper.
    # SECURITY DEFINER bypasses the policy for the membership lookup only.
    op.execute(
        r"""
        CREATE OR REPLACE FUNCTION multitenancy.resolve_user_first_membership(
            p_user_id uuid
        )
        RETURNS TABLE(workspace_id uuid, cell_id uuid)
        LANGUAGE plpgsql
        STABLE
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $func$
        BEGIN
            IF p_user_id IS NULL THEN
                RAISE EXCEPTION 'p_user_id cannot be NULL';
            END IF;

            RETURN QUERY
            SELECT c.workspace_id, m.cell_id
            FROM multitenancy.cell_members m
            JOIN multitenancy.cells c ON c.id = m.cell_id
            WHERE m.user_id = p_user_id
              AND c.archived_at IS NULL
            ORDER BY m.joined_at ASC
            LIMIT 1;
        END;
        $func$;
        """
    )

    op.execute(
        "GRANT EXECUTE ON FUNCTION multitenancy.resolve_user_first_membership(uuid) "
        "TO oriion_app;"
    )

    op.execute(
        "COMMENT ON FUNCTION multitenancy.resolve_user_first_membership(uuid) IS "
        "'Returns (workspace_id, cell_id) for the user''s oldest active cell membership. "
        "SECURITY DEFINER because the caller has no tenant GUC set yet — by design — "
        "and would otherwise hit default-deny RLS on cell_members. "
        "Single production caller: _shared.middleware.tenant_context.get_tenant_db_session.';"
    )


def downgrade() -> None:
    op.execute(
        "DROP FUNCTION IF EXISTS multitenancy.resolve_user_first_membership(uuid);"
    )
    op.execute(
        "DROP FUNCTION IF EXISTS multitenancy.bootstrap_first_workspace(uuid, text, text);"
    )
