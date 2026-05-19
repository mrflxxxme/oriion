-- =====================================================================
-- Bounded context: rbac (Role-Based Access Control — system level)
-- Owner: Oriion backend / rbac-implementer
-- Authoritative source per ADR-024. Phase-specs MUST NOT duplicate DDL.
--
-- Naming (per ADR-024 §2 — naming corrections, STRICT):
--   * Table is `system_roles`   — NOT `roles_rbac` (deprecated).
--   * Table is `permissions`    — granular `resource.action` slugs.
--   * Table is `role_assignments` — user ↔ scope ↔ role binding.
--
-- This context covers SYSTEM-LEVEL access control: "who can do what at the
-- organization/cell boundary". It is distinct from `agents.agent_archetypes`
-- which models AI persona roles inside a vertical template.
--
-- Scope of this file:
--   * system_roles     — built-in role catalogue
--   * permissions      — granular permission catalogue
--   * role_permissions — many-to-many grant table
--   * role_assignments — (user, scope_type, scope_id, role) binding
--
-- Cross-context refs:
--   * role_assignments.user_id    → iam.users.id
--   * role_assignments.scope_id   → multitenancy.workspaces.id
--                                  OR multitenancy.cells.id
--                                  (resolved by scope_type)
--
-- NAMING (2026-05-19): the `organization` scope value was renamed to
--   `workspace` along with the multitenancy DDL rename. `scope_type` enum
--   is now `('workspace','cell')`.
-- =====================================================================

-- ---------------------------------------------------------------------
-- Table: system_roles
-- Purpose:
--   Built-in role catalogue. Slugs are stable identifiers used by the API
--   and by client code. is_built_in=true rows are seeded and immutable
--   (enforced at the application layer; the DB does not protect them).
-- ---------------------------------------------------------------------
CREATE TABLE rbac.system_roles (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    slug          text NOT NULL UNIQUE,
    display_name  text NOT NULL,
    description   text,
    is_built_in   boolean NOT NULL DEFAULT true,
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE rbac.system_roles IS 'System-level roles. NOT to be confused with agents.agent_archetypes (AI personas).';

-- ---------------------------------------------------------------------
-- Table: permissions
-- Purpose:
--   Granular permission catalogue. Slug format is strictly `<resource>.<action>`
--   (e.g. `cell.create`, `member.invite`, `billing.view`, `agent.run`).
--   Permissions are immutable: additions require a migration + ADR.
-- ---------------------------------------------------------------------
CREATE TABLE rbac.permissions (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    slug          text NOT NULL UNIQUE
        CHECK (slug ~ '^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$'),
    display_name  text NOT NULL,
    description   text,
    category      text NOT NULL,
    created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX permissions_category_idx ON rbac.permissions (category);

COMMENT ON COLUMN rbac.permissions.slug IS 'Format: <resource>.<action>. Lowercase; underscores allowed within segments.';

-- ---------------------------------------------------------------------
-- Table: role_permissions
-- Purpose:
--   Many-to-many bridge granting a permission to a role.
-- ---------------------------------------------------------------------
CREATE TABLE rbac.role_permissions (
    role_id        uuid NOT NULL REFERENCES rbac.system_roles(id) ON DELETE CASCADE,
    permission_id  uuid NOT NULL REFERENCES rbac.permissions(id)  ON DELETE RESTRICT,
    granted_at     timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (role_id, permission_id)
);

CREATE INDEX role_permissions_permission_id_idx ON rbac.role_permissions (permission_id);

-- ---------------------------------------------------------------------
-- Table: role_assignments
-- Purpose:
--   Binds a user to a role within a scope. scope_type discriminates whether
--   scope_id references multitenancy.organizations.id or
--   multitenancy.cells.id. Cross-context FKs are NOT materialized as
--   FOREIGN KEY constraints (see ADR-024 — preserves microservice split).
-- ---------------------------------------------------------------------
CREATE TABLE rbac.role_assignments (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      uuid NOT NULL,  -- → iam.users.id
    scope_type   text NOT NULL CHECK (scope_type IN ('workspace','cell')),
    scope_id     uuid NOT NULL,  -- → multitenancy.workspaces.id OR .cells.id
    role_id      uuid NOT NULL REFERENCES rbac.system_roles(id) ON DELETE RESTRICT,
    assigned_by  uuid,           -- → iam.users.id (nullable: system / bootstrap)
    assigned_at  timestamptz NOT NULL DEFAULT now(),
    expires_at   timestamptz
);

CREATE UNIQUE INDEX role_assignments_unique_uidx
    ON rbac.role_assignments (user_id, scope_type, scope_id, role_id);

CREATE INDEX role_assignments_user_idx
    ON rbac.role_assignments (user_id);

CREATE INDEX role_assignments_scope_idx
    ON rbac.role_assignments (scope_type, scope_id);

CREATE INDEX role_assignments_expiring_idx
    ON rbac.role_assignments (expires_at)
    WHERE expires_at IS NOT NULL;

-- =====================================================================
-- RLS — role_assignments only
-- A user sees their own assignments unconditionally. Admins/owners in
-- the same scope see all assignments in that scope (enforced via app
-- layer + SECURITY DEFINER procedures; the RLS policy here implements
-- the user-sees-own baseline).
-- =====================================================================
ALTER TABLE rbac.role_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE rbac.role_assignments FORCE  ROW LEVEL SECURITY;

CREATE POLICY role_assignments_select_self
    ON rbac.role_assignments
    FOR SELECT
    USING (user_id = _shared.current_user_id());

-- Admin/owner visibility is granted at app layer via BYPASSRLS service
-- account when the caller holds the appropriate `*.admin` permission.

-- =====================================================================
-- Seed data — built-in roles + core permissions + default mappings
-- The values below are AUTHORITATIVE for Wave 0. The migration that runs
-- this file MUST insert them; subsequent migrations MAY add permissions
-- but MUST NOT mutate existing slugs.
--
-- Commented out here so this file remains pure DDL; the implementer
-- materializes seeds via a separate `seed_rbac.sql` invoked from the
-- Alembic migration.
-- =====================================================================
--
-- INSERT INTO rbac.system_roles (slug, display_name, description) VALUES
--   ('owner',   'Owner',   'Full control of the workspace including billing.'),
--   ('admin',   'Admin',   'Full control of a cell; no billing/workspace-delete.'),
--   ('editor',  'Editor',  'Create / run tasks and agents; manage non-billing settings.'),
--   ('viewer',  'Viewer',  'Read-only access to cell content.'),
--   ('billing', 'Billing', 'View invoices and manage payment methods; no content access.'),
--   ('guest',   'Guest',   'Time-boxed limited access (e.g. for friends-loop participants).');
--
-- INSERT INTO rbac.permissions (slug, display_name, category, description) VALUES
--   ('workspace.view',   'View workspace',  'workspace', 'Read workspace metadata.'),
--   ('workspace.update', 'Edit workspace',  'workspace', 'Mutate workspace metadata.'),
--   ('workspace.delete', 'Delete workspace','workspace', 'Soft-delete the workspace.'),
--   ('cell.create',         'Create cell',        'cell',         'Create a new cell in the org.'),
--   ('cell.view',           'View cell',          'cell',         'Read cell metadata.'),
--   ('cell.update',         'Edit cell',          'cell',         'Mutate cell metadata / settings.'),
--   ('cell.archive',        'Archive cell',       'cell',         'Archive a cell.'),
--   ('member.invite',       'Invite member',      'member',       'Issue invitations.'),
--   ('member.remove',       'Remove member',      'member',       'Remove a member from a cell.'),
--   ('member.role_change',  'Change member role', 'member',       'Reassign a member to a different system role.'),
--   ('billing.view',        'View billing',       'billing',      'Read invoices and balances.'),
--   ('billing.manage',      'Manage billing',     'billing',      'Manage payment methods and plan tier.'),
--   ('agent.run',           'Run agent',          'agent',        'Trigger an AI agent run.'),
--   ('task.create',         'Create task',        'task',         'Create a new task.'),
--   ('task.view',           'View task',          'task',         'Read a task and its artefacts.');
