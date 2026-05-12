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
| Структура | `app/` (Next.js App Router) + `components/` + `lib/` + `features/<bounded_context>/` |
| Размер файла | < 400 строк |
| Imports | Абсолютные через `@/*` |
| Accessibility | ARIA labels обязательны, контраст AA минимум |

## Git и PR

| Аспект | Правило |
|---|---|
| Branching | `feature/<phase-id>-<slug>` для фаз, `fix/<slug>` для багов, `hotfix/<slug>` для prod |
| Commits | Conventional Commits: `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:` |
| Атомарность | Один commit = одно логическое изменение. Squash при merge — опция при необходимости |
| PR title | `[Phase-<id>] <краткое описание>` или `[Fix] <описание>` |
| PR description | Шаблон: Goal / Changes / Tests / Checklist / Linked phase / ADR refs |
| Размер PR | < 500 строк изменений (исключения для генерируемого кода, миграций) |

## Tier-based review (ADR-015)

| Tier | Примеры | Auto-merge | AI-review | Human review |
|---|---|---|---|---|
| **1** | Docs, format, lint-fix, dependency bumps (patch) | ✅ если CI зелёный | — | — |
| **2** | Tests, simple refactors, copy changes | ❌ | 1 AI | Опционально |
| **3** | New endpoint, new component, новая фича | ❌ | 1 AI | 1 human |
| **4** | Архитектурные изменения, security, migrations, billing | ❌ | 2 AI (code + security) | 2 human (senior+) |
| **5** | Hotfix в prod | ❌ | 1 AI | 1 senior expedited |

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
