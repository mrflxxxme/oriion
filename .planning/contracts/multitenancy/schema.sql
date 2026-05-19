-- =====================================================================
-- Bounded context: multitenancy (Workspaces & Cells)
-- Owner: Oriion backend / multitenancy-implementer
-- Authoritative source per ADR-024. Phase-specs MUST NOT duplicate DDL.
--
-- ⚠️ NAMING (revised 2026-05-19): previously `organizations` — renamed to
--    `workspaces` as part of pre-Phase-00.3 contract extension to align DDL
--    with the IAM API surface (`workspace_id` returned by /api/v1/auth/register)
--    and the cross-context stubs that Phase 00.2 already merged. The legacy
--    term `organization` is retired; do not introduce it in new code.
--
-- Scope of this file:
--   * workspaces     — billing/legal tenant (1 workspace → N cells)
--                      (was `organizations` pre-2026-05-19)
--   * cells          — workspace boundary (= AI team per ADR-009)
--   * cell_members   — user ↔ cell membership with system role assignment
--
-- RLS: ENABLED on all three tables. Per-request the app sets THREE GUCs
--      (per ADR-009 amendment 2026-05-19, layered RLS model):
--      SET LOCAL app.current_user_id      = '<uuid>'
--      SET LOCAL app.current_workspace_id = '<uuid>'
--      SET LOCAL app.current_cell_id      = '<uuid>'
--      (FastAPI dependency `get_tenant_db_session`). multitenancy.* policies
--      use the `user_id` membership model (default-deny on missing GUC).
--
-- Cross-context refs:
--   * cell_members.user_id  → iam.users.id     (see contracts/iam/schema.sql)
--   * cell_members.role_id  → rbac.system_roles.id (see contracts/rbac/schema.sql)
-- =====================================================================

-- ---------------------------------------------------------------------
-- Table: workspaces
-- Purpose:
--   Legal / billing tenant. One workspace holds N cells; subscription
--   and invoicing happen at this level (see `billing` context). In the
--   public API this entity is exposed as `workspace` (per IAM API contract).
-- ---------------------------------------------------------------------
CREATE TABLE multitenancy.workspaces (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    slug            text NOT NULL,
    display_name    text NOT NULL,
    billing_email   citext,
    country_code    char(2) NOT NULL DEFAULT 'RU',
    timezone        text NOT NULL DEFAULT 'Europe/Moscow',
    plan_tier       text NOT NULL DEFAULT 'free'
        CHECK (plan_tier IN ('free','starter','pro','enterprise')),
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now(),
    deleted_at      timestamptz
);

CREATE UNIQUE INDEX workspaces_slug_active_uidx
    ON multitenancy.workspaces (slug)
    WHERE deleted_at IS NULL;

CREATE INDEX workspaces_plan_tier_idx
    ON multitenancy.workspaces (plan_tier)
    WHERE deleted_at IS NULL;

COMMENT ON TABLE multitenancy.workspaces IS 'Billing / legal tenant (was `organizations` pre-2026-05-19). Soft-delete cascades cells to archived state (not hard delete).';

-- ---------------------------------------------------------------------
-- Table: cells
-- Purpose:
--   Workspace boundary per ADR-009. Each cell is an "AI team" with its own
--   credit balance, secrets, sandbox context. vertical_template_slug is a
--   loose reference to `verticals/<slug>/` (string match, not FK).
-- ---------------------------------------------------------------------
CREATE TABLE multitenancy.cells (
    id                          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id                uuid NOT NULL REFERENCES multitenancy.workspaces(id) ON DELETE RESTRICT,
    slug                        text NOT NULL,
    display_name                text NOT NULL,
    vertical_template_slug      text,
    settings_jsonb              jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at                  timestamptz NOT NULL DEFAULT now(),
    updated_at                  timestamptz NOT NULL DEFAULT now(),
    archived_at                 timestamptz
);

CREATE UNIQUE INDEX cells_workspace_slug_uidx
    ON multitenancy.cells (workspace_id, slug);

CREATE INDEX cells_workspace_id_idx
    ON multitenancy.cells (workspace_id)
    WHERE archived_at IS NULL;

CREATE INDEX cells_vertical_template_idx
    ON multitenancy.cells (vertical_template_slug)
    WHERE archived_at IS NULL AND vertical_template_slug IS NOT NULL;

COMMENT ON TABLE  multitenancy.cells IS 'Workspace = AI team per ADR-009. Archived (soft) on workspace soft-delete.';
COMMENT ON COLUMN multitenancy.cells.vertical_template_slug IS 'Loose FK to verticals/<slug>/ (string match by convention).';

-- ---------------------------------------------------------------------
-- Table: cell_members
-- Purpose:
--   user ↔ cell membership. role_id is the system role at the cell scope.
--   Invitations are materialized rows with invited_by + last_active_at;
--   the invite token itself lives in a sibling table (see `api.yaml`).
-- ---------------------------------------------------------------------
CREATE TABLE multitenancy.cell_members (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    cell_id         uuid NOT NULL REFERENCES multitenancy.cells(id) ON DELETE CASCADE,
    user_id         uuid NOT NULL,  -- → iam.users.id
    role_id         uuid NOT NULL,  -- → rbac.system_roles.id
    joined_at       timestamptz NOT NULL DEFAULT now(),
    invited_by      uuid,           -- → iam.users.id (nullable: owner self-join)
    last_active_at  timestamptz
);

CREATE UNIQUE INDEX cell_members_cell_user_uidx
    ON multitenancy.cell_members (cell_id, user_id);

CREATE INDEX cell_members_user_id_idx
    ON multitenancy.cell_members (user_id);

CREATE INDEX cell_members_role_id_idx
    ON multitenancy.cell_members (role_id);

COMMENT ON TABLE multitenancy.cell_members IS 'User membership in a cell with a system role. Cross-context FKs enforced at app layer.';

-- =====================================================================
-- RLS — Row Level Security
-- All three tables are RLS-enabled. Policies key off the per-request GUC
-- `app.current_user_id` (membership pattern). The application MUST set
-- it on every transaction:
--     SET LOCAL app.current_user_id = '<uuid>';
-- A missing/invalid GUC yields zero rows (default-deny).
--
-- Per ADR-009 amendment 2026-05-19 (3-GUC layered model): the application
-- also sets `app.current_workspace_id` and `app.current_cell_id` for use
-- by `llm_gateway.*` and per-cell tables respectively. multitenancy.*
-- policies remain membership-driven via `_shared.current_user_id()`.
-- =====================================================================

ALTER TABLE multitenancy.workspaces    ENABLE ROW LEVEL SECURITY;
ALTER TABLE multitenancy.workspaces    FORCE  ROW LEVEL SECURITY;
ALTER TABLE multitenancy.cells         ENABLE ROW LEVEL SECURITY;
ALTER TABLE multitenancy.cells         FORCE  ROW LEVEL SECURITY;
ALTER TABLE multitenancy.cell_members  ENABLE ROW LEVEL SECURITY;
ALTER TABLE multitenancy.cell_members  FORCE  ROW LEVEL SECURITY;

-- Helper: extract current user id from GUC, return NULL on missing.
-- Defined in `_shared/0002_current_user_id_helper.py` migration.
--   CREATE FUNCTION _shared.current_user_id() RETURNS uuid ...

-- Workspaces: visible to anyone who is a member of any cell in the workspace.
CREATE POLICY workspaces_select_own
    ON multitenancy.workspaces
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1
            FROM multitenancy.cells c
            JOIN multitenancy.cell_members m ON m.cell_id = c.id
            WHERE c.workspace_id = workspaces.id
              AND m.user_id = _shared.current_user_id()
        )
    );

-- Cells: visible to its members.
CREATE POLICY cells_select_member
    ON multitenancy.cells
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1
            FROM multitenancy.cell_members m
            WHERE m.cell_id = cells.id
              AND m.user_id = _shared.current_user_id()
        )
    );

-- Cell members: a member sees co-members within the same cell.
CREATE POLICY cell_members_select_co_member
    ON multitenancy.cell_members
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1
            FROM multitenancy.cell_members self
            WHERE self.cell_id = cell_members.cell_id
              AND self.user_id = _shared.current_user_id()
        )
    );

-- Write policies (insert/update/delete) are intentionally NOT defined here.
-- Mutations go through service-account connections that bypass RLS via
-- SECURITY DEFINER stored procedures or BYPASSRLS role. Authorization is
-- enforced at the application layer by the `rbac` context.
