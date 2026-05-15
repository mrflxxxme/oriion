# Wave 0 — Foundation (3 недели)

> **Revision 2026-05-15:** Wave 0 anchor changed из «WB-Селлер vertical team» на «horizontal `productivity-core` team». WB-Селлер team-preset переезжает в Wave 2. See [Session-decision](../../JOURNAL.md) + [ADR-017](../../decisions/ADR-017-vertical-templates.md) + [ADR-029](../../decisions/ADR-029-master-agent-vertical-templates.md).

## Цель волны

**Internal demo:** horizontal team-preset `productivity-core` («Твои личные ассистенты») — Coordinator + Researcher + Writer + Analyst — end-to-end через DeepSeek + YandexGPT + GigaChat.

**Demo-сценарий (фиксированный для reproducible runs):** «Market & content brief для нового продукта».

User input:
> «Запускаем платформу AI-команд для SMB в РФ. Сделай нам market brief + контент-план первого месяца».

Pipeline:
1. Coordinator → план из 3 sub-tasks
2. Researcher: `web_search` → топ-3 конкурента + 5 boards/communities + 3 тренда
3. Analyst: LLM-reasoning (без Pyodide в Wave 0) → TAM/SAM-оценка + competitive matrix + positioning
4. Writer: marketing brief + контент-план + tone-of-voice doc
5. Coordinator: synthesizes → 3 артефакта + final summary

Acceptance артефактов:
- `brief.md` ≥ 1500 слов (TAM/SAM, top-3 конкурента, ICP, позиционирование, GTM hint)
- `competitive-matrix.md` — markdown-таблица ≥5×4
- `content-plan.md` — 10 постов с заголовками + outline + платформа + tone

Budgets:
- End-to-end latency ≤120 sec (3 parallel LLM-calls)
- Cost ≤30¢ per demo run

End-to-end pipeline: auth → DB (cell) → LLM-gateway (3 провайдера + BYOK) → Pydantic-AI runtime → MCP-инфра (built-in `web_search` + `read_url`) → ответ.

## Критерий перехода к Wave 1

- Все phase'ы Wave 0 помечены `Done`
- Internal demo проходит вживую перед командой
- CI зелёный, все CI-gates работают (lint/types/tests/SAST/secrets/SBOM)
- Один разработчик может развернуть локально через `docker compose up` за ≤10 мин

## Scope

**Must-have:**
- Monorepo + CI/CD + dev-окружение (Vite + FastAPI + GitHub Actions + GitLab mirror)
- Custom JWT auth (email/password + verification + refresh tokens)
- PostgreSQL 16 + pgvector + RLS + cell-aware schemas
- LLM-gateway: DeepSeek (V3+R1) + YandexGPT + GigaChat + BYOK для 3 провайдеров
- MCP-client infrastructure (built-in `web_search` + `read_url`; production MCP-серверы — W1+)
- Pydantic-AI runtime: **horizontal team-preset `productivity-core` (Coordinator + Researcher + Writer + Analyst)** per [ADR-017](../../decisions/ADR-017-vertical-templates.md) revision
- **Deep role-prompts** для 4 ролей в [`contracts/role-prompts/`](../../contracts/role-prompts/) — 9-секционная структура, first-draft в Phase 00.5 (hardening pass — Phase 01.1 retro)
- Docker Compose deploy + Caddy reverse proxy
- OpenTelemetry → Grafana (минимум)
- **Frontend skeleton (Phase 00.7 NEW per Session 4 / C-D2):** functional Wave-0 demo UI — auth + cell-list + task-submit + SSE result view, materializing все 18 components из `ui/component-inventory.md` через ui-ux-pro-max designer workflow

**Nice-to-have (можно отложить в Wave 1):**
- Yandex ID / VK ID OAuth
- 2FA TOTP
- Magic-link login
- Memory (cell + role) — Wave 1
- Artifacts versioning (Yjs) — Wave 1
- Master-Agent layer (vertical templates) — Wave 1+ per [ADR-029](../../decisions/ADR-029-master-agent-vertical-templates.md)
- WB-Селлер vertical-template (graduated W0→W2 per Session-2026-05-15)

## Длительность и команда

- **Срок:** 3 недели
- **Команда:** Tech Lead (full), Senior Backend (full), DevOps (0.5 FTE)

## Метрика успеха

| Метрика | Цель |
|---|---|
| End-to-end demo (WB team) проходит | Pass/Fail |
| Время на cold-start dev environment | ≤10 мин |
| Время на регистрацию + первая задача (API) | ≤2 мин |
| CI pipeline runtime | ≤8 мин |
| Test coverage нового кода | ≥70% |

## Risks specific

- **R-04 (runaway costs):** budget hard-caps per task + per agent + per cell — обязательны с дня 1
- **R-08 (регуляторика):** РКН-уведомление подано ДО Phase 00.2
- **R-12 (scope creep):** strictly must-have, никаких «давайте сделаем красиво»

## Артефакты к концу волны

- Working monorepo + GitHub Actions CI + GitLab mirror
- Custom JWT auth — регистрация / verify / login / refresh / logout работают
- Postgres + RLS + cell-aware migrations работают
- LLM-gateway: `/api/llm/generate` отвечает через DeepSeek-V3, DeepSeek-R1, YandexGPT-Pro, GigaChat-Pro
- BYOK UI: пользователь может подключить свой DeepSeek/Yandex/GigaChat key
- MCP-client framework в backend (built-in `web_search` + `read_url`; готов принимать external MCP-серверы)
- `productivity-core` team-preset: Coordinator decomposes задачу → Researcher + Writer + Analyst выполняют → 3 артефакта (brief.md + competitive-matrix.md + content-plan.md)
- Deep role-prompts (4 файла, ~2000+ слов каждый) в `contracts/role-prompts/` — first-draft, hardening pass запланирован в Phase 01.1 retro
- Docker Compose разворачивает всё локально
- Grafana показывает: API metrics, LLM provider availability, request latencies, per-role cost rollup
- Staging deploy через GitHub Actions работает

## Phases

См. [PHASES.md](./PHASES.md).
