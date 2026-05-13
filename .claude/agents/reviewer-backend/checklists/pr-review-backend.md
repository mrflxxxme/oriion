# Checklist — backend PR review

Run top-to-bottom. Any unchecked `must` item → `verdict: request_changes`
with `severity: block`. Cite `file:line` for every finding.

## 1. api.yaml conformance (must)

- [ ] Every new/changed endpoint exists in `_meta/contracts/<context>/api.yaml`.
- [ ] Path, HTTP verb, path-params, query-params, request body shape match.
- [ ] Response body schema matches for every documented status code.
- [ ] Status codes used in implementation are a subset of those documented.
- [ ] Auth/security scheme on the endpoint matches the contract.
- [ ] If contract drift is intentional → reject; require contract PR first
      per P-INIT-2 (contract is authoritative).

## 2. schema.sql conformance (must)

- [ ] Every new/changed table, column, index, constraint appears in
      `_meta/contracts/<context>/schema.sql`.
- [ ] Column types, nullability, defaults match.
- [ ] FK relationships (referenced table, ON DELETE/UPDATE) match.
- [ ] RLS policies declared for tables in iam / multitenancy / billing
      contexts (per memory.md per-context invariants).
- [ ] No use of deprecated columns (e.g. `ui_sprite_archetype` per
      ADR-024). Replacement: `agent_archetype_id`.

## 3. Alembic migration safety (must — if migration present)

Delegate to `checklists/migration-safety.md`. Every `must` line there
becomes a `must` line here.

## 4. Test coverage (must)

- [ ] Every new public function with branching has ≥1 unit test covering
      happy path.
- [ ] Every new public function with branching has ≥1 unit test covering
      an edge / error path.
- [ ] Every new endpoint has ≥1 integration test (happy) + ≥1 integration
      test (one edge: invalid input OR auth failure OR conflict).
- [ ] Tests are deterministic: no `time.sleep`, no real-network, no
      random seeds without fixing.
- [ ] Fixtures reset DB state between cases (no leakage).
- [ ] `pytest --collect-only` succeeds; `pytest -q` exits 0 on a clean
      branch checkout.

## 5. Error handling (must)

- [ ] No bare `except:`.
- [ ] No `except Exception:` at API boundary without log + re-raise / map.
- [ ] HTTP errors raise typed `HTTPException(status_code=..., detail=...)`
      with status matching api.yaml.
- [ ] Domain errors are typed exceptions, not strings or dicts.
- [ ] Retryable errors (network, DB transient) wrapped with explicit
      retry policy where applicable.

## 6. Structured logging (must)

- [ ] Use repo logger (`from observability.logger import get_logger`), not
      `print` or root `logging`.
- [ ] Boundary calls log `phase_id`, `request_id`, `actor` (cell_id or
      user_id), `op` (operation name).
- [ ] No PII in log message (emails, tokens, full prompts).
- [ ] No f-string formatting in log calls (`logger.info("x=%s", x)`, not
      `logger.info(f"x={x}")`).

## 7. Secrets & DLP (must)

- [ ] No literal API key / token / secret in source.
- [ ] No literal DB URI in source.
- [ ] All env-driven via `pydantic_settings.BaseSettings`.
- [ ] No `.env` checked into the diff.
- [ ] No secret in test fixtures (use `pytest.fixture` with env override
      or factory).

## 8. Bounded-context discipline (must)

- [ ] No cross-context import bypassing the contract layer (e.g. `iam`
      directly importing `billing` SQLAlchemy models).
- [ ] Cross-context calls go via documented events
      (`_meta/contracts/<context>/events.yaml`) or via public API client.

## 9. Style (should)

- [ ] `ruff check` passes on the diff.
- [ ] `mypy` passes on touched modules (no new ignores without comment
      explaining why).
- [ ] Function length < 60 lines where reasonable (refactor or comment
      otherwise).
