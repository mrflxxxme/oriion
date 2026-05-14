# Wave 0 — Foundation (3 недели)

## Цель волны

**Internal demo:** WB-Селлер team-preset (Coordinator + Listing Writer + Researcher) end-to-end через DeepSeek + YandexGPT + GigaChat. Пользователь ставит задачу через API → workflow → artifact.

End-to-end pipeline: auth → DB (cell) → LLM-gateway (3 провайдера + BYOK) → Pydantic-AI runtime → MCP-инфра → ответ.

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
- MCP-client infrastructure (без production MCP-серверов, только built-in web_search)
- Pydantic-AI runtime: WB-Селлер team-preset (Coordinator + Listing Writer + Researcher)
- Docker Compose deploy + Caddy reverse proxy
- OpenTelemetry → Grafana (минимум)
- **Frontend skeleton (Phase 00.7 NEW per Session 4 / C-D2):** functional Wave-0 demo UI — auth + cell-list + task-submit + SSE result view, materializing все 18 components из `_meta/ui/component-inventory.md` через ui-ux-pro-max designer workflow

**Nice-to-have (можно отложить в Wave 1):**
- Yandex ID / VK ID OAuth
- 2FA TOTP
- Magic-link login
- Memory (cell + role) — Wave 1
- Artifacts versioning (Yjs) — Wave 1

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
- LLM-gateway: `/api/llm/generate` отвечает через DeepSeek-V3, YandexGPT-Pro, GigaChat-Pro
- BYOK UI: пользователь может подключить свой DeepSeek/Yandex/GigaChat key
- MCP-client framework в backend (готов принимать MCP-серверы)
- WB-Селлер team-preset: Coordinator decomposes задачу → Listing Writer + Researcher выполняют → artifact
- Docker Compose разворачивает всё локально
- Grafana показывает: API metrics, LLM provider availability, request latencies
- Staging deploy через GitHub Actions работает

## Phases

См. [PHASES.md](./PHASES.md).
