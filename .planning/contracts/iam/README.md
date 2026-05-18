# Bounded context: `iam` — Identity & Access Management

**Status:** DRAFT-READY (Milestone B, Wave 0 full context per ADR-024)
**Authoritative source per ADR-024 / P-INIT-2.**
Phase-specs MUST import via cross-link; they MUST NOT duplicate DDL/OpenAPI/events.

## Purpose

The `iam` bounded context owns the **canonical person record** and the
**proof-of-identity primitives**: passwords, sessions, refresh tokens, and
external IdP linkages. It does not own organizational membership, roles, or
permissions — those are the responsibility of `multitenancy` and `rbac`.

A successful authentication produces a `user_id` plus an access/refresh token
pair. Downstream contexts (`multitenancy`, `rbac`, `tasks`, `billing`) consume
the `user_id` and never reach into `iam` tables directly.

## Ubiquitous language

| Term | Meaning |
|---|---|
| **User** | A person. One row in `iam.users`. Identified by `id` (uuid) and a unique email. |
| **Session** | An active login on one device/browser. Has `expires_at` and may be revoked. |
| **RefreshToken** | A single-use credential that mints a new access+refresh pair. Belongs to a `rotation_chain_id`. |
| **RotationChain** | The set of refresh tokens descended from one login. Reuse of a used token revokes the entire chain. |
| **OAuthLink** | A mapping `(provider, provider_user_id) → user_id` with encrypted provider tokens. |

**Out of scope for `iam`:**
- Organizations, cells, cell membership → `multitenancy`
- Roles and permissions → `rbac`
- Billing entities → `billing`
- AI roles (`agent_archetypes`) → `agents`

## Invariants

1. Email is stored **case-insensitively** via the `citext` type. The unique
   constraint excludes soft-deleted rows so a re-registration after purge is
   possible.
2. Password is **always** `argon2id`. A `CHECK` constraint enforces this at
   the DB layer. Legacy algorithms (`md5`, `sha1`, `bcrypt-legacy`) MUST NOT
   be introduced — migrate, do not extend.
3. RefreshToken is **single-use**. Presenting a token whose `used_at IS NOT
   NULL` is treated as a reuse attack: the implementer MUST revoke every
   token sharing the same `rotation_chain_id` and emit
   `oriion.iam.session.revoked.v1` with `reason=security_incident`.
4. **Soft delete only** for users — `deleted_at` flags the row; a retention
   job performs the hard purge after the configured retention window
   (ФЗ-152 / GDPR compliant). `oriion.iam.user.deleted.v1` carries the
   retention horizon for downstream subscribers.
5. OAuth provider tokens are stored **encrypted** (AES-256-GCM, KMS key per
   environment). Plaintext MUST NOT be logged.
6. **Consent (`pdn`)** is **mandatory** before `POST /auth/register` completes
   (FZ-152 art. 9). Missing or `false` value MUST yield 422 with
   `code: iam.consent.pdn_missing`. The Privacy Policy / consent-form
   `version` in effect at grant time is pinned in `iam.consents.version`
   and never mutated retroactively. Revocation is soft (`revoked_at`).
   Every consent grant/revoke MUST emit `oriion.iam.user.consent_recorded.v1`
   AND write an immutable row to `audit.audit_log` via
   `audit.emit_audit_event(action='iam.consent.granted'|'iam.consent.revoked', actor_id=user_id, payload={kind, version})`.
7. **Email-verification tokens** are single-use, expire in **24h**, and stored
   as **SHA-256 hex hashes** — plaintext goes only over email. Re-requesting
   a token revokes any prior unused tokens for the same user.
8. **Password-reset tokens** are single-use, expire in **1h**, stored as
   SHA-256 hashes, and belong to a `reset_chain_id`. Presenting a token
   whose `used_at IS NOT NULL` is a reuse attack: the implementer MUST
   revoke every token sharing the same `reset_chain_id` AND revoke every
   active session for the user (emitting `oriion.iam.session.revoked.v1`
   with `reason=security_incident`).
9. **Anti-enumeration**: `POST /auth/forgot-password` and
   `POST /auth/resend-verification` MUST always respond with `202 Accepted`
   regardless of whether the email exists. Rate-limit responses (429) are
   acceptable; any other status reveals account existence.

## RLS

**Not applicable.** `iam` is a system-level context. Access control happens
at the application layer (service accounts + endpoint scopes). Per-tenant
isolation is provided by the `multitenancy` context, which references
`iam.users.id`.

## Cross-context dependencies

This context is **referenced by**:
- `multitenancy` — `cell_members.user_id` → `iam.users.id`
- `rbac` — `role_assignments.user_id` → `iam.users.id`
- `tasks`, `billing`, `agents` — `created_by_user_id`, `actor_user_id`, etc.

This context **references** (architect-PR 2026-05-17):
- `multitenancy.provision_initial_workspace(user_id) -> {workspace_id, cell_id}` — called
  **synchronously** by `POST /auth/register` to seed the user's first workspace + cell.
  IDs are returned in `RegisterResponse`. The 00.2 worktree imports a stub at
  `backend/src/_stubs/multitenancy.py`; the real impl ships from Phase 00.3 at
  `backend/src/multitenancy/services/workspace_service.py`; Phase 00.2.5 integration
  swaps the import.
- `audit.emit_audit_event(...)` — called for every auth-action (register / login /
  logout / refresh / consent.granted|revoked / email_verified / password_reset.*).
  Stub at `backend/src/_stubs/audit.py`; real impl from Phase 00.3 at
  `backend/src/audit/services/audit_service.py`.

These cross-context calls were introduced by the architect-PR to support the
full-scope auth flow (consent recording + first-workspace provisioning at register).
Before architect-PR, `iam` had no outgoing dependencies; this is now a deliberate
exception, scoped to the register/auth-event path only.

## Events emitted

See [`events.yaml`](./events.yaml). Notable consumers:
- `multitenancy` listens to `oriion.iam.user.registered.v1` to seed a personal
  organization on first sign-up (Wave 1+).
- `billing` listens to `oriion.iam.user.deleted.v1` to schedule data export
  before the retention horizon.

## ADR references

- [ADR-024](../../decisions/ADR-024-bounded-context-contracts.md) — folder
  layout + CloudEvents 1.0.
- [ADR-007](../../decisions/ADR-007-authentik-then-keycloak.md) — auth stack
  evolution; `iam` is the local-state side of that stack.
- [ADR-009](../../decisions/ADR-009-multitenancy-3-levels.md) — multitenancy
  reference (separate context).
- [ADR-014](../../decisions/ADR-014-security.md) — encryption / KMS rules.
- [ADR-010](../../decisions/ADR-010-role-versioning.md) — versioning policy
  applies to `api.yaml` (`/v1` URL major + SemVer in `info.version`).

## Phase references

- **Architect-PR (pre-00.2)** — Extended this contract with `consents`,
  `email_verification_tokens`, `password_reset_tokens` tables + 4 new
  endpoints (verify-email / resend-verification / forgot-password /
  reset-password) + 4 new CloudEvents + `_shared` Alembic bootstrap
  migration (extensions + schema namespacing + `set_updated_at()` trigger
  function). This absorbs Phase 00.3's bootstrap step so Phases 00.2 /
  00.3 / 00.4 can run in 3-way parallel.
- **Phase 00.2** — Auth implementation (registration with consent + initial
  workspace provisioning, login, refresh-rotation, logout, email
  verification, password reset, `/users/me`). Owns
  `backend/migrations/versions/iam/`.
- **Phase 00.3** — Multitenancy + audit + RLS (no longer owns schema
  bootstrap — done in architect-PR). Owns `backend/migrations/versions/{multitenancy,audit}/`
  and `backend/src/_shared/db/rls.py`.
- **Phase 00.5** — WB-Seller vertical scaffolding consumes user identity for
  attribution / audit but does not extend the `iam` schema.

## Implementation notes (non-authoritative)

- Alembic migrations live under `backend/migrations/versions/iam/` per ADR-024 §4.
- The `_shared.set_updated_at()` trigger function is defined in the global
  migration bootstrap; this context just wires triggers per table.
- Access-token format is JWT (HS256 in Wave 0 with rotating secret; RS256 in
  Wave 2+ when Authentik fronts the stack per ADR-007).
