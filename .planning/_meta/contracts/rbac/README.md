# Bounded context: `rbac` — Role-Based Access Control (system level)

**Status:** DRAFT-READY (Milestone B, Wave 0 full context per ADR-024)
**Authoritative source per ADR-024 / P-INIT-2.**

## Purpose

The `rbac` context owns **system-level authorization**: who can perform
which system operations (create cell, invite member, view billing, run an
agent) within which **scope** (organization or cell). It is the answer to
the question "is this user allowed to do this action here?" and is the only
context that holds the system role catalogue and the permission catalogue.

`rbac` is **not** about runtime AI behaviour. Domain-level permissions that
live inside agent runs (which MCP tools an `agent_archetype` may invoke,
what data a workflow may read) belong to the `agents` and `mcp` contexts.

## Ubiquitous language

| Term | Meaning |
|---|---|
| **system_roles** | Built-in roles for **people doing system operations**: `owner`, `admin`, `editor`, `viewer`, `billing`, `guest`. STRICT name per ADR-024 §2. |
| **permissions** | Granular capability tokens shaped as `<resource>.<action>` (e.g. `cell.create`, `member.invite`, `billing.view`). |
| **role_permissions** | Many-to-many bridge granting a permission to a role. |
| **role_assignments** | A `(user, scope_type, scope_id, role)` binding with optional `expires_at`. |
| **scope_type** | `organization` or `cell` — determines which `multitenancy` table `scope_id` references. |

**Crucial disambiguation — DO NOT CONFUSE:**

- `system_roles` (this context) = **people** doing system operations.
- `agent_archetypes` (contract: `agents`) = **AI personas** declared by a
  vertical template (e.g. WB-Seller "researcher", "listing_writer").
  These are two unrelated catalogues.

**Deprecated terms (per ADR-024 §2 — MUST NOT appear in new code):**
- `roles_rbac` → use `system_roles`.
- `roles_agent` → use `agent_archetypes` (in the `agents` context).
- `sprite-ID` / `ui_sprite_archetype` → use `agent_archetype_id`.

## Invariants

1. **Naming is strictly** `system_roles`, `permissions`, `role_assignments`
   — P-AUDIT-2 enforcement. Any use of `roles_rbac` / `roles_agent` /
   `ui_sprite_archetype` in implementations is a bug.
2. **Built-in roles are immutable** (`is_built_in = true`). They cannot be
   deleted; their slugs cannot change. New roles MAY be added in future
   migrations but require an ADR.
3. **Permissions are immutable**. Adding a permission requires a migration
   + ADR; renaming or deleting one is a breaking change and goes through
   the same gate.
4. **Scope match invariant.** A role assignment's `scope_type` must match
   the role's design intent. Examples:
   - `billing` role is meaningful only at `scope_type = organization`.
   - `editor` / `viewer` roles are meaningful only at `scope_type = cell`.
   - `owner` is meaningful only at `scope_type = organization`.
   The API rejects mismatches with `rbac.assignment.scope_mismatch`. The DB
   does not encode the mapping — it lives in the role metadata seed and is
   validated application-side.
5. **Permission slug format** is enforced by a `CHECK` constraint:
   `^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$`. Lowercase, single dot, snake_case
   per segment.
6. `(user_id, scope_type, scope_id, role_id)` is **unique** in
   `role_assignments`. A user cannot have the same role twice in the same
   scope.

## RLS

- `role_assignments` has RLS enabled. The baseline policy lets a user
  **see their own assignments**. Admins/owners reading assignments in
  their scope go through `BYPASSRLS` service-account procedures whose
  authorization is enforced application-side via the `*.admin`-class
  permissions.
- `system_roles`, `permissions`, `role_permissions` are catalogue tables,
  not user data, and are read by all authenticated users without RLS.

## Cross-context dependencies

This context **references** (via cross-context FKs declared in comments,
not as physical FOREIGN KEYs — preserves microservice extraction):

- `role_assignments.user_id` → `iam.users.id`
- `role_assignments.scope_id` → `multitenancy.organizations.id`
  **or** `multitenancy.cells.id` (per `scope_type`)

This context is **referenced by**:

- `multitenancy.cell_members.role_id` → `rbac.system_roles.id`
- Every endpoint in every other context — `rbac` is the canonical answer
  to "is this allowed?".

## Events

See [`events.yaml`](./events.yaml). Three events:

- `oriion.rbac.role_assigned.v1`
- `oriion.rbac.role_revoked.v1`
- `oriion.rbac.role_expired.v1` (emitted by the retention/expiry sweeper)

Audit pipeline consumes all three.

## ADR references

- [ADR-024](../../../decisions/ADR-024-bounded-context-contracts.md) — naming
  corrections (this context's reason to exist as a separate file).
- [ADR-009](../../../decisions/ADR-009-multitenancy-3-levels.md) — scope
  semantics (organization vs cell).
- [ADR-014](../../../decisions/ADR-014-security.md) — security posture
  surrounding admin-class permissions.
- [ADR-007](../../../decisions/ADR-007-authentik-then-keycloak.md) — auth
  provider; `rbac` consumes the authenticated principal but does not depend
  on the IdP.

## Phase references

- **Phase 00.2** — Auth implementation wires `/users/me/permissions` into
  the JWT claim resolver used by FastAPI dependencies.
- **Phase 00.3** — DB + RLS bootstrap creates the `rbac` schema and runs
  the seed migration that materializes built-in roles and permissions.
- **Phase 00.4** — Cell provisioning auto-assigns the creating user the
  `owner` role at organization scope (emitting `role_assigned.v1`).

## Implementation notes (non-authoritative)

- Alembic migrations under `backend/alembic/versions/rbac/`. Seed values
  live in a separate `seed_rbac.sql` invoked from the migration so the
  authoritative DDL file stays pure structure.
- A periodic job calls `_shared.expire_role_assignments()` to flip
  expired rows and emit `role_expired.v1`. Implementation lives in the
  `tasks` context (sweeper) but reads/writes here.
- Computing effective permissions for `/users/me/permissions` is a join
  over `role_assignments → role_permissions → permissions` with a scope
  filter. The implementer SHOULD cache the result per (user, scope) with
  invalidation on `role_assigned.v1` / `role_revoked.v1` /
  `role_expired.v1`.
