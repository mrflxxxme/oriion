# ADR-015: AI-dev-процесс — 6 ролей + tier-based ревью + изоляция от prod

- **Status:** Accepted

## Decision

Полный AI-dev-стек:

### 1. Tier-based ревью
См. таблицу в [conventions.md](../_meta/conventions.md#tier-based-review-adr-015).

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
- Merge в main — через PR с CI-gates и tier-review
- Sync feature-веток с main — раз в день (минимизация rebase-боли)

### 5. Observability + cost caps
- Langfuse-инстанс для dev-agents (отдельно от prod)
- Метрики per-agent: PR throughput, acceptance rate, average review iterations, token cost, bug introduction rate, test coverage delta, security findings
- Cost caps: per-task ($5 Sonnet / $20 Opus), per-day per-agent ($50), per-week total ($1000 на старте)
- Kill-switch: 30 мин без прогресса → auto-abort

### 6. 6 специализированных AI-ролей
| Роль | Mandate | Tools |
|---|---|---|
| **Planner** | Декомпозиция, dependencies, оценка | `gsd:plan-phase` / `oh-my-claudecode:plan` |
| **Coder** | Имплементация | `coder` agent |
| **Tester** | Unit + integration + golden updates | `tester` agent |
| **Reviewer** | Code review каждого PR | `code-reviewer` agent |
| **Security-Auditor** | SAST, secrets, supply-chain, threat model | `security-auditor` agent |
| **DevOps** | CI/CD, IaC, observability | `devops-automator` agent |

### 7. Поддерживающие практики
- **ADR обязательны** при значимых решениях; AI-агент ссылается на ADR в PR
- **Архитектурные ретро** раз в 2 нед: AI-Architect анализирует merge'd PR за период, выявляет техдолг
- **Системные промпты AI-агентов** — версионируются как код (`.claude/` + `AGENTS.md`)
- **Knowledge persistence** через claude-mem / project memory
- **License-scanner** блокирует GPL/AGPL в deps
- **DR runbook «AI agent went rogue»**: kill-switch, отзыв credentials, аудит последних N PR

## Consequences

- Скорость dev'а × 2-4 при сохранении качества
- Защита от классов багов AI (галлюцинации, уязвимости)

## Links

- Risk: [R-06](../risks/REGISTER.md)
- Conventions: [_meta/conventions.md](../_meta/conventions.md)
- Protocol: [_meta/agent-protocol.md](../_meta/agent-protocol.md)
