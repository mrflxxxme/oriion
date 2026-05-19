# Bounded context: `multitenancy` — Workspaces & Cells

**Status:** DRAFT-READY (Milestone B, Wave 0 full context per ADR-024)
**Authoritative source per ADR-024 / P-INIT-2.**

## Naming bridge (2026-05-19)

> ⚠️ **Renamed pre-Phase-00.3:** `organizations` → `workspaces`. The DDL and
> public API now use **`workspace` / `workspace_id`** everywhere. The
> previous term `organization` is retired. The cross-context stubs landed in
> the architect-PR (`backend/src/_stubs/multitenancy.py`) and the IAM API
> `RegisterResponse.workspace_id` are now consistent with this DDL.
>
> If you see `organization` in legacy artefacts (older ADRs, archived
> session-context files) treat it as the same entity. New code MUST use
> `workspace`.

## Purpose

The `multitenancy` context owns the **primary tenancy boundary** of the
platform: the **workspace → cell → cell_member** hierarchy. Per ADR-009
the cell is the unit of billing, RLS isolation, quotas, and per-tenant
configuration (LLM stack preference, secrets path, audit stream).

Every multi-tenant table elsewhere in the system carries a `cell_id` (or, less
commonly, a `workspace_id`); all visibility / authorization downstream is
expressed in those terms.

## Ubiquitous language

| Term | Meaning |
|---|---|
| **Workspace** | The legal entity holding the subscription and receiving invoices. One workspace, N cells. (Was `organization` pre-2026-05-19.) |
| **Cell** | A workspace = an AI team per ADR-009. Has its own credit balance, secrets path, sandbox context, audit stream. |
| **CellMember** | A `(cell, user)` pair augmented with a system role. The atomic unit of "who can do what in this cell". |
| **Invitation** | A pending CellMember addressed by email + token (lives in a sibling table referenced by the API; not modelled in this `schema.sql` to keep the W0 surface tight). |
| **vertical_template_slug** | Loose reference (string match) to `verticals/<slug>/`. Not a DB FK by design — vertical templates evolve independently of the schema. |

**Not in scope here:**
- User identity itself (`iam`).
- Roles and permissions (`rbac`).
- Credit balances / pricing tables (`billing`).

## Invariants

1. A **cell belongs to exactly one workspace** (`workspace_id NOT NULL`,
   `ON DELETE RESTRICT` — workspaces cannot be hard-deleted while they hold cells).
2. A **user can be a member of many cells**, including cells across different
   workspaces.
3. `cell_members (cell_id, user_id)` is **unique** — a user has at most one
   membership row per cell. Role changes update the row in place and emit
   `oriion.multitenancy.member.role_changed.v1`.
4. `vertical_template_slug` is **not a database FK**. It references
   `verticals/<slug>/` by string match. Implementers MUST validate the
   slug exists at the application layer.
5. **RLS is enabled on all three tables.** Reads are scoped to memberships of
   the calling user. Writes go through service-account connections that
   bypass RLS via stored procedures; the `rbac` context authorizes those
   procedures.
6. **Soft-delete on workspaces cascades to archival** (not deletion) of
   their cells. Hard purge is owned by the retention job.

## RLS — 3-GUC layered model (revised 2026-05-19)

Per ADR-009 amendment, the FastAPI dependency
`get_tenant_db_session(user, cell_id)` sets THREE Postgres session locals on
every tenant-scoped transaction:

```sql
SET LOCAL app.current_user_id      = '<uuid>';
SET LOCAL app.current_workspace_id = '<uuid>';
SET LOCAL app.current_cell_id      = '<uuid>';
```

Each downstream context picks the GUC that matches its filter granularity:

| Context | GUC used | Why |
|---|---|---|
| `multitenancy.*`  | `app.current_user_id` (membership EXISTS) | Visibility tied to per-cell membership |
| `llm_gateway.byok_keys` | `app.current_workspace_id` | BYOK is workspace-scoped |
| `billing.credit_transactions`, future `tasks.*`, `memory.*` | `app.current_cell_id` | Per-cell hot tables; O(1) filter |
| `rbac.role_assignments` | `app.current_user_id` (self) | Baseline self-row visibility |

A missing or invalid GUC results in zero rows (default-deny). The shared
helper `_shared.current_user_id()` returns `NULL` on missing GUC so all
policies naturally evaluate to FALSE.

Write policies are intentionally not defined at the RLS layer. Mutations
flow through `SECURITY DEFINER` procedures or a `BYPASSRLS` service role;
authorization is enforced application-side using the `rbac` context.

## Cross-context dependencies

This context **references**:
- `iam.users.id` from `cell_members.user_id` and `cell_members.invited_by`
  (cross-context FKs declared in comments; enforced at the application layer).
- `rbac.system_roles.id` from `cell_members.role_id`.

This context is **referenced by**:
- `tasks` — `task.cell_id` ownership scope.
- `billing` — `credit_transactions.cell_id`.
- `agents`, `mcp`, `llm-gateway`, `artifacts`, `memory` — all multi-tenant
  rows carry `cell_id` and/or `workspace_id`.

## Events

See [`events.yaml`](./events.yaml). Notable consumers:
- `billing` listens to `oriion.multitenancy.workspace.plan_changed.v1` to
  recompute entitlements.
- `agents` listens to `oriion.multitenancy.cell.created.v1` to seed the
  default team preset from the vertical template.

## ADR references

- [ADR-024](../../decisions/ADR-024-bounded-context-contracts.md) — contracts
  layout.
- [ADR-009](../../decisions/ADR-009-multitenancy-3-levels.md) — cell as
  first-class domain concept; B+/C/D isolation tiers; **3-GUC RLS amendment
  2026-05-19**.
- [ADR-007](../../decisions/ADR-007-authentik-then-keycloak.md) — auth
  stack (consumes user identity).
- [ADR-014](../../decisions/ADR-014-security.md) — RLS + secrets posture.

## Service contract — symbols consumed by other contexts

Added by the architect-PR (2026-05-17) to make the cross-context dependency
from `iam` to `multitenancy` explicit. Real implementations ship from Phase
00.3; stubs in `backend/src/_stubs/multitenancy.py` while phases 00.2 / 00.3
run in parallel.

```python
# backend/src/multitenancy/services/workspace_service.py (real impl — Phase 00.3)
class WorkspaceProvisionResult(BaseModel):
    workspace_id: UUID         # = multitenancy.workspaces.id
    cell_id: UUID              # = multitenancy.cells.id

async def provision_initial_workspace(user_id: UUID) -> WorkspaceProvisionResult:
    """Seed the user's first workspace + initial trial cell.

    Called synchronously by iam.auth_service.register() AFTER the user row is
    persisted and BEFORE the email-verification token is issued (so the user
    has a valid {workspace_id, cell_id} on first login).

    Invariants:
      - Exactly one workspace + one cell per user from this call.
      - Workspace name = user's email-localpart (mutable later by user).
      - Cell tier = 'trial' (per ADR-009); trial_expires_at = now() + 14 days.
      - Idempotent on (user_id) — re-invocation returns existing IDs.
    """
```

## Phase references

- **Phase 00.3** — DB + RLS bootstrap (creates `multitenancy` tables, RLS
  policies; produces real impl of `provision_initial_workspace`). NOTE: the
  schema bootstrap (CREATE SCHEMA, extensions, `_shared` trigger) is **NOT**
  Phase 00.3 anymore — done in architect-PR `_shared/0001_init.py`.
- **Phase 00.4** — Cell provisioning workflow per ADR-009 (billing webhook →
  cell-provisioner).
- **Phase 00.5** — WB-Seller vertical scaffolding uses `vertical_template_slug
  = 'wb-seller'` on cell create.

## Implementation notes (non-authoritative)

- Alembic migrations under `backend/migrations/versions/multitenancy/`.
- Cross-context FKs (to `iam.users`, `rbac.system_roles`) are declared in
  table comments and validated by integration tests; we do not create
  physical FOREIGN KEY constraints across context schemas to preserve the
  extract-to-microservice option (ADR-024 Consequences).
- Trial cells / TTL cleanup (ADR-009 Wave 1 scope) will extend `cells` with
  a `trial_expires_at` column; out of scope for this draft.
- Per-cell schema (`cell_<uuid>`) and its `memory_entries` table are
  created eagerly inside `provision_cell()` via the SQL function
  `multitenancy.provision_cell_schema(uuid)`. Cell archive does NOT drop
  the schema (retention 3y per FZ-152). DROP deferred to Wave 3 cleanup.
