# Bounded context: `multitenancy` — Organizations & Cells

**Status:** DRAFT-READY (Milestone B, Wave 0 full context per ADR-024)
**Authoritative source per ADR-024 / P-INIT-2.**

## Purpose

The `multitenancy` context owns the **primary tenancy boundary** of the
platform: the **organization → cell → cell_member** hierarchy. Per ADR-009
the cell is the unit of billing, RLS isolation, quotas, and per-tenant
configuration (LLM stack preference, secrets path, audit stream).

Every multi-tenant table elsewhere in the system carries a `cell_id` (or, less
commonly, an `organization_id`); all visibility / authorization downstream is
expressed in those terms.

## Ubiquitous language

| Term | Meaning |
|---|---|
| **Organization** | The legal entity holding the subscription and receiving invoices. One organization, N cells. |
| **Cell** | A workspace = an AI team per ADR-009. Has its own credit balance, secrets path, sandbox context, audit stream. |
| **CellMember** | A `(cell, user)` pair augmented with a system role. The atomic unit of "who can do what in this cell". |
| **Invitation** | A pending CellMember addressed by email + token (lives in a sibling table referenced by the API; not modelled in this `schema.sql` to keep the W0 surface tight). |
| **vertical_template_slug** | Loose reference (string match) to `_meta/verticals/<slug>/`. Not a DB FK by design — vertical templates evolve independently of the schema. |

**Not in scope here:**
- User identity itself (`iam`).
- Roles and permissions (`rbac`).
- Credit balances / pricing tables (`billing`).

## Invariants

1. A **cell belongs to exactly one organization** (`organization_id NOT NULL`,
   `ON DELETE RESTRICT` — orgs cannot be hard-deleted while they hold cells).
2. A **user can be a member of many cells**, including cells across different
   organizations.
3. `cell_members (cell_id, user_id)` is **unique** — a user has at most one
   membership row per cell. Role changes update the row in place and emit
   `oriion.multitenancy.member.role_changed.v1`.
4. `vertical_template_slug` is **not a database FK**. It references
   `_meta/verticals/<slug>/` by string match. Implementers MUST validate the
   slug exists at the application layer.
5. **RLS is enabled on all three tables.** Reads are scoped to memberships of
   the calling user. Writes go through service-account connections that
   bypass RLS via stored procedures; the `rbac` context authorizes those
   procedures.
6. **Soft-delete on organizations cascades to archival** (not deletion) of
   their cells. Hard purge is owned by the retention job.

## RLS — explicit policy snippets

The application MUST set the current user on every request transaction:

```sql
SET LOCAL app.current_user_id = '<uuid>';
```

A missing or invalid GUC results in zero rows (default-deny). The shared
helper `_shared.current_user_id()` returns `NULL` on missing GUC so all
policies naturally evaluate to FALSE.

Read policies (see `schema.sql` for full DDL):

- `organizations` — visible to a user who is a member of **any cell** in that
  organization.
- `cells` — visible to its **direct members**.
- `cell_members` — visible to **co-members** of the same cell.

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
- `billing` — `invoice.organization_id`, `credit_balance.cell_id`.
- `agents`, `mcp`, `llm-gateway`, `artifacts`, `memory` — all multi-tenant
  rows carry `cell_id`.

## Events

See [`events.yaml`](./events.yaml). Notable consumers:
- `billing` listens to `oriion.multitenancy.organization.plan_changed.v1` to
  recompute entitlements.
- `agents` listens to `oriion.multitenancy.cell.created.v1` to seed the
  default team preset from the vertical template.

## ADR references

- [ADR-024](../../../decisions/ADR-024-bounded-context-contracts.md) — contracts
  layout.
- [ADR-009](../../../decisions/ADR-009-multitenancy-3-levels.md) — cell as
  first-class domain concept; B+/C/D isolation tiers.
- [ADR-007](../../../decisions/ADR-007-authentik-then-keycloak.md) — auth
  stack (consumes user identity).
- [ADR-014](../../../decisions/ADR-014-security.md) — RLS + secrets posture.

## Phase references

- **Phase 00.3** — DB + RLS bootstrap (creates `multitenancy` schema, applies
  this DDL, wires the `app.current_user_id` middleware).
- **Phase 00.4** — Cell provisioning workflow per ADR-009 (billing webhook →
  cell-provisioner).
- **Phase 00.5** — WB-Seller vertical scaffolding uses `vertical_template_slug
  = 'wb-seller'` on cell create.

## Implementation notes (non-authoritative)

- Alembic migrations under `backend/alembic/versions/multitenancy/`.
- Cross-context FKs (to `iam.users`, `rbac.system_roles`) are declared in
  table comments and validated by integration tests; we do not create
  physical FOREIGN KEY constraints across context schemas to preserve the
  extract-to-microservice option (ADR-024 Consequences).
- Trial cells / TTL cleanup (ADR-009 Wave 1 scope) will extend `cells` with
  a `trial_expires_at` column; out of scope for this draft.
