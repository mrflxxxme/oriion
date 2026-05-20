# Conventions — code, tests, process

> Не повторять в phase-файлах. Если фаза нарушает convention — это надо обосновать в самой фазе.

## Python (backend)

| Аспект | Правило |
|---|---|
| Версия | Python 3.12, использовать `match`, type hints везде |
| Форматтер | `ruff format` (replaces black) — auto в pre-commit |
| Линтер | `ruff check --select=ALL --ignore=...` (конфиг в `pyproject.toml`) |
| Type checker | `mypy --strict` для всего `src/`, для тестов — без `--strict` |
| Тесты | `pytest` + `pytest-asyncio` + `pytest-cov`. Coverage ≥70% для нового кода, ≥85% для security-critical |
| Async | Все I/O через `httpx`, `asyncpg`, `redis.asyncio`. Никаких блокирующих вызовов в async-функциях |
| Pydantic | v2, модели — единственная граница типов между слоями |
| Структура | Модульный монолит: `src/<bounded_context>/` (billing, agents, runtime, artifacts, iam, collaboration) |
| Размер файла | < 500 строк (хард-лимит — split на модули) |
| Imports | `isort` через ruff, абсолютные импорты от корня пакета |
| Env / config | Pydantic Settings, никаких magic strings в коде |
| Secrets | Никогда в коде. `.env.example` коммитим, `.env` — нет |
| Logging | `structlog`, JSON-формат в prod, OpenTelemetry трейсы автоматом |

## TypeScript (frontend)

| Аспект | Правило |
|---|---|
| Версия | TypeScript 5.6+ strict mode |
| Форматтер | Prettier через CI и pre-commit |
| Линтер | ESLint + plugin:@typescript-eslint/recommended-type-checked |
| Тесты | Vitest для unit, Playwright для e2e |
| State | Zustand для глобального, TanStack Query для server state |
| Стили | Tailwind v4 + shadcn/ui компоненты, без CSS-in-JS |
| Структура | `frontend/src/routes/` (TanStack file-based router) + `frontend/src/components/` + `frontend/src/lib/` + `frontend/src/features/<bounded_context>/` — per [ADR-001](../decisions/ADR-001-modular-monolith.md) (revised) |
| Размер файла | < 400 строк |
| Imports | Абсолютные через `@/*` |
| Accessibility | ARIA labels обязательны, контраст AA минимум |

## Git и PR

| Аспект | Правило |
|---|---|
| Branching | `claude/<adjective-noun-hash>` для AI-led sessions (default, e.g. `claude/heuristic-rhodes-f7a3ef`) или `feature/<phase-id>-<slug>` для human-led фаз; `fix/<slug>` для багов; `hotfix/<slug>` для prod. Phase-id живёт в PR title (`[NN.M] ...`), не в имени ветки |
| Commits | Conventional Commits: `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:` |
| Атомарность | Один commit = одно логическое изменение. Squash при merge — опция при необходимости |
| PR title | `[Phase-<id>] <краткое описание>` или `[Fix] <описание>` |
| PR description | Шаблон: Goal / Changes / Tests / Checklist / Linked phase / ADR refs |
| Размер PR | < 500 строк изменений (исключения для генерируемого кода, миграций) |

## Tier-based review

**Source of truth:** [ADR-027 §tier-table](../decisions/ADR-027-solo-ai-git-pr-workflow.md) — 5 tiers с AI reviewers (per ADR-023 11-role catalog) + Founder approval per [P-INIT-3](../decisions/ADR-028-policies-registry.md#policies-canonical-home) (Founder = always final approver tier 3+).

Не дублируем tier-table инлайн. При изменении tier-policy — обновляется ADR-027, не этот файл.

## CI gates (обязательно для каждого PR)

```
1. Lint (ruff, eslint)
2. Type-check (mypy strict, tsc strict)
3. Unit tests + coverage gate
4. Integration tests
5. Security: Semgrep, Bandit, gitleaks, pip-audit, npm audit
6. SBOM (Syft) + vuln scan (Grype)
7. License scan (forbid GPL/AGPL в deps)
8. Container scan (Trivy)
9. Migration safety (squawk)
10. Golden dataset regression (если меняется role prompt)
11. Performance benchmark на критичных endpoints
```

Любой fail = блок merge. Bypass только через explicit override + human approval + ADR-обоснование.

## Tests

| Тип | Стек | Цель |
|---|---|---|
| Unit | pytest / vitest | Логика функций, без I/O |
| Integration | pytest + testcontainers (Postgres, Redis) | Реальная БД, очереди |
| E2E (backend) | pytest + httpx + dev-сервер | API contracts |
| E2E (frontend) | Playwright | User flows |
| Load | k6 или Locust | Перед каждой волной + квартально |
| Security | OWASP ZAP + custom | Перед public-релизами |
| Golden role | LLM-as-judge на 50–200 задач | Каждое изменение role prompt |

### Router-test convention (F-P5-5, ratified Phase 00.5b Commit 3)

Two-layer pattern to cover both per-router handler behaviour AND main.py mount integrity, without duplicating assertions:

| Layer | Where | Pattern | What it catches |
|---|---|---|---|
| **Mini-app router unit tests** | `tests/<context>/unit/test_routers.py` | Build a throw-away `FastAPI()` inside the test fixture, `app.include_router(...)` the router under test, install bounded-context exception handlers manually (mirror of `tests/multitenancy/test_workspaces_router.py::_install_multitenancy_handler`), drive via in-process `httpx.AsyncClient(transport=ASGITransport(app=app))`. DI overrides scoped to the throw-away app — no global state. | Handler logic regressions, DI seam wiring, exception envelope shape per RFC 7807. |
| **Main-app mount smoke** | `tests/integration/test_main_app_routes.py` | Pull the live `app` from `src.main`, parametrize over the expected `(path, method)` pairs, inspect `app.routes` directly. No HTTP calls — purely static introspection. Stays in default `not integration and not live` filter. | "Router accidentally dropped from `main.include_router(...)`" regressions; path/prefix drift between router module and main wiring. |

**Why both:** the mini-app pattern keeps router unit tests fast and isolated (no full app boot), but it can't catch "I forgot to include this router in main.py" — because the unit test always wires its own throw-away app. The mount-smoke layer plugs that gap at near-zero cost (15 parametrized cases, sub-second runtime, no fixtures).

**When to extend:** new router → add a mini-app unit test under `tests/<context>/unit/test_routers.py` AND add the (path, method) pair to `_EXPECTED_ROUTES` in `tests/integration/test_main_app_routes.py`. The mount-smoke also has a `test_all_routers_mounted_under_api_v1` aggregate gap-listing helper that fires when multiple routes are missing simultaneously (e.g. someone deleted two `include_router(...)` lines in one commit).

## Documentation

- README в каждом пакете/модуле (1 параграф + примеры).
- Docstrings: PEP 257 / TSDoc на public-API.
- ADR при значимых решениях (см. [decisions/](../decisions/)).
- Runbook'и в `docs/runbooks/` для эксплуатации.
- OpenAPI генерируется из FastAPI автоматически, публикуется в Stoplight/Redoc.

## Process

- Weekly planning (понедельник 60 мин)
- Daily async standup в Telegram (текст)
- Weekly retro (пятница 30 мин)
- Milestone review по завершению каждой волны
- Quarterly Strategic Review (полный день)

## Definition of Done (для фазы)

- [ ] Все tasks помечены done
- [ ] Все acceptance criteria выполнены и проверены тестами
- [ ] CI зелёный, coverage gate пройден
- [ ] Документация обновлена (README, OpenAPI, runbook'и)
- [ ] ADR создан/обновлён при значимых решениях
- [ ] Risks register обновлён при новых рисках
- [ ] PR(s) сревьюено по tier-таблице
- [ ] Deployment в staging успешен, smoke-тесты прошли
- [ ] Метрика успеха фазы измерена и зафиксирована
