# ADR-015: AI-dev operational hygiene (isolation, observability, kill-switch)

- **Status:** Accepted

> **Scope change vs предыдущая версия:** этот ADR ранее покрывал шесть тем (tier-review, CI-gates, prod-isolation, worktree, observability, 6 ролей, supporting practices). После [ADR-028 policies registry](./ADR-028-policies-registry.md) mandate переразделён:
> - **Tier-based review** → [ADR-027](./ADR-027-solo-ai-git-pr-workflow.md) (re-thought tier-table для solo + AI).
> - **AI-роли (6 → 11) + spawning + AgentDB** → [ADR-023](./ADR-023-ai-team-runtime.md).
> - **Здесь остаётся:** operational hygiene — изоляция от prod, worktree-per-task, observability + cost-caps, supporting practices.

## Decision

### 1. Tier-based ревью

См. [ADR-027 секцию "Tier-table (re-thought для solo + AI)"](./ADR-027-solo-ai-git-pr-workflow.md#5-tier-table-re-thought-для-solo--ai).

### 2. CI-gates (обязательны для каждого PR)

См. [conventions.md → CI gates](../_meta/conventions.md#ci-gates).

### 3. AI изолирован от prod

- AI-агенты работают в dev/staging only
- Никаких production credentials в их контексте — секреты только в production CI (GitHub Actions secrets с OIDC к Yandex Cloud)
- Production deploy — через `release-manager` workflow с human approval (GitHub Environments protection rules)
- Миграции prod-БД — ручной запуск инженером с предварительным dry-run в staging
- Read-only зеркало prod-данных (с обфускацией ПДн) в staging для AI-агентов с realistic dataset

### 4. Worktree-изоляция параллельных AI-агентов

- Каждая задача → отдельный git-worktree
- Один agent = одна ветка = одна задача в моменте
- Task broker держит file-locks: если файл редактируется в активной ветке — новая задача либо в очередь либо отклонена
- Merge в main — через PR с CI-gates и tier-review (см. [ADR-027](./ADR-027-solo-ai-git-pr-workflow.md))
- Sync feature-веток с main — раз в день (минимизация rebase-боли)

### 5. Observability + cost caps

- Langfuse-инстанс для dev-agents (отдельно от prod)
- Метрики per-agent: PR throughput, acceptance rate, average review iterations, token cost, bug introduction rate, test coverage delta, security findings
- **Cost cap policy** — конкретные пороги (per-task, per-day, per-team monthly, Sonnet fallback rules) задаются founder'ом в `.claude/agents/_shared/cost-budget.yaml` (см. [ADR-023](./ADR-023-ai-team-runtime.md)). Этот ADR фиксирует только operational guardrails — без числовых деталей. Mitigation owner — [R-31](../risks/REGISTER.md)
- Kill-switch: 30 мин без прогресса → auto-abort

### 6. AI-роли

Состав ролей и pipeline-шаблон — см. [ADR-023 — AI-team runtime](./ADR-023-ai-team-runtime.md). Текущая модель: 11 persistent Opus-ролей (cross-cutting + implementation + quality gates) + non-persistent роли spawned per phase. Расширена с предыдущей 6-ролевой модели под solo + AI team per GRILL DECISION-3.

### 7. Поддерживающие практики

- **ADR обязательны** при значимых решениях; AI-агент ссылается на ADR в PR
- **Архитектурные ретро** раз в 2 нед: AI-Architect анализирует merge'd PR за период, выявляет техдолг
- **Системные промпты AI-агентов** — версионируются как код (`.claude/` + `AGENTS.md`)
- **Knowledge persistence** через claude-mem / project memory + AgentDB namespaces (см. [ADR-023 §7](./ADR-023-ai-team-runtime.md#7-agentdb-namespaces))
- **License-scanner** блокирует GPL/AGPL в deps
- **DR runbook «AI agent went rogue»**: kill-switch, отзыв credentials, аудит последних N PR
- **Handoff-сообщения между ролями** — CloudEvents 1.0 envelope (см. `.claude/agents/_shared/handoff-schema.json` per [ADR-023](./ADR-023-ai-team-runtime.md))

## Consequences

- Скорость dev'а × 2-4 при сохранении качества
- Защита от классов багов AI (галлюцинации, уязвимости)
- Operational hygiene mandate чёткий: этот ADR — про «как не сжечь production, не утечь данные, не зависнуть в бесконечном loop'е»; кто и как пишет код — в ADR-023; как код попадает в main — в ADR-027

## Links

- Risk: [R-06](../risks/REGISTER.md), [R-31](../risks/REGISTER.md)
- Conventions: [_meta/conventions.md](../_meta/conventions.md)
- Protocol: [_meta/agent-protocol.md](../_meta/agent-protocol.md)
- Related ADRs: [ADR-023](./ADR-023-ai-team-runtime.md) (AI-team runtime), [ADR-027](./ADR-027-solo-ai-git-pr-workflow.md) (Git/PR workflow)
