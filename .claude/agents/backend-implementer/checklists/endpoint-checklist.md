# Checklist — Endpoint implementation

Прогоняется перед каждым commit при Workflow 1 (new/updated endpoint). All items checked
or explicit N/A с rationale.

## Contract conformance

- [ ] `_meta/contracts/<context>/api.yaml` прочитан полностью для целевого endpoint
- [ ] Path, method точно matches spec
- [ ] Request body Pydantic schema fields ↔ api.yaml `requestBody` schema 1:1 (names,
      types, optional/required, defaults, validation constraints)
- [ ] Response body Pydantic schema fields ↔ api.yaml `responses.<code>.content.<type>.schema` 1:1
- [ ] HTTP status codes (success + error) match api.yaml `responses` keys
- [ ] Security schemes applied per api.yaml `security` requirement (e.g. `Depends(get_current_user)` для JWT)
- [ ] Tags applied per api.yaml `tags` field
- [ ] Никакая правка `_meta/contracts/` НЕ сделана. Если spec gap — escalation, не silent fix.

## Code quality

- [ ] `async def` для endpoint function (per project async-first)
- [ ] Type-annotated fully — params, return type, internal vars
- [ ] No mutable default arguments
- [ ] No bare `except:` — always typed exception
- [ ] No `print()` — use structured logger (`structlog` or project's)
- [ ] No hardcoded values which should be config (DB URL, secret keys, magic numbers)
- [ ] No commented-out code in commit

## Pydantic schemas

- [ ] `BaseModel` from Pydantic v2
- [ ] `model_config = ConfigDict(...)` (not old `Config` class)
- [ ] `Field(...)` для validation constraints
- [ ] `EmailStr`, `HttpUrl`, etc. для typed validation где applicable
- [ ] Alias config if api.yaml uses camelCase (`alias` + `populate_by_name=True`)

## Service / repository

- [ ] Business logic в service layer, NOT в router
- [ ] Repository thin (no business logic, only data access)
- [ ] Dependency injection через FastAPI `Depends()` для DB session, current_user, services
- [ ] Async DB session (`AsyncSession`) — no sync engine

## Bounded context isolation (ADR-024 §1)

- [ ] No direct imports `from src.<other-context>` в `src/<this-context>/`
- [ ] Cross-context interaction через published API or events (per `_meta/contracts/<other>/api.yaml` или `events.yaml`)
- [ ] If cross-context need exists which isn't published — escalate к architect

## RLS / multi-tenancy

- [ ] Endpoint requiring tenant context uses `current_setting('app.current_tenant')` через middleware
- [ ] No `WHERE organization_id = X` hardcoded — RLS делает изоляцию
- [ ] Verified: query без tenant context fails (test это покрывает)

## Naming

- [ ] Canonical naming везде: `agent_archetype_id`, `system_roles`, `agent_archetypes`
- [ ] No deprecated terms: `roles_rbac`, `roles_agent`, `sprite_id`, `ui_sprite_archetype`
- [ ] Snake_case columns в DB, snake_case Python vars
- [ ] API field aliases per api.yaml convention (камелCase если spec — camelCase)

## Tests

- [ ] ≥1 unit test для Pydantic schema validation (happy + invalid)
- [ ] ≥1 unit test для service logic (mocked repository)
- [ ] ≥1 integration test для endpoint (test client + test DB)
- [ ] Test названия mapped к acceptance checks из PLAN.md
- [ ] All tests pass: `pytest backend/tests/<context>/ -v`

## CloudEvents (если endpoint эмитит)

- [ ] Event type ↔ `events.yaml` `type` field 1:1
- [ ] Event source format: `claude-agent://backend-implementer/<context>`
- [ ] Event data payload — Pydantic-validated
- [ ] Emit ПОСЛЕ успешной business transaction (не до)

## Lint / type

- [ ] `ruff check backend/src/<context>/` — clean
- [ ] `ruff format backend/src/<context>/` — applied
- [ ] `mypy --strict backend/src/<context>/` — clean (no `Any`, no missing types)

## Commit

- [ ] Atomic — endpoint + tests в одном commit (если small); split if multiple distinct units
- [ ] Conventional Commits format: `<type>(<bounded-context>): <description>`
- [ ] Commit message includes ADR-027 §4 fields: Phase, Pipeline-role, Reviewers, ADR-refs
- [ ] Co-Authored-By line присутствует
- [ ] No secrets в diff (pre-commit grep check)

## Memory

- [ ] Pattern stored в `agent-memory:backend-implementer` (если successful)
- [ ] Task complete entry в `phase-state:<phase-id>`

## CloudEvent emit

- [ ] `tech.oriion.code.commit.v1` payload prepared
- [ ] Validated against `_shared/handoff-schema.json`
- [ ] Emitted к `reviewer-backend` AND `reviewer-security` (parallel)
- [ ] Только ПОСЛЕ successful `git commit` (sha captured)
