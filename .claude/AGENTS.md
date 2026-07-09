---
title: Oriion AI-team — entry point + routing-table
type: agent-runtime-entrypoint
status: living document
authoritative-source: ../.planning/decisions/ADR-023-ai-team-runtime.md
last-updated: 2026-05-13
---

# `.claude/AGENTS.md` — Oriion AI-team entry-point

> Точка входа для spawning AI-агентов в проекте Oriion. Описывает **КТО** входит в команду (11 persistent Opus-ролей + non-persistent), **КАК** они расписаны по слоям и **КАК** оркестрируются в pipeline'ах.
>
> Source-of-truth для конкретики ролей — [ADR-023](../.planning/decisions/ADR-023-ai-team-runtime.md). Если этот файл и ADR-023 расходятся — победил ADR-023.

---

## Контекст модели

Oriion исполняется в режиме **solo founder + 11 persistent Opus AI-агентов + non-persistent роли spawned per phase** (зафиксировано в [P-INIT-5](../.planning/_meta/GRILL-DECISIONS-ORIION.md#3-policy-decisions-cross-session-stable)). Founder — единственный человек в loop'е; AI-агенты выполняют весь implementation и review, founder утверждает merge для tier 3+ PR.

Все persistent роли подняты на **Opus как primary model-tier** (full quality budget). Tier 1-2 routine задачи могут fallback на Sonnet через `agents/_shared/cost-budget.yaml` (см. global rule §4 ниже). Tier 3+ задачи всегда Opus.

Spawning runtime — native Claude Code `Task` tool с `subagent_type=<role>`. Каждая из 11 ролей — **спавнабельный нативный сабагент** `agents/<role>.md` (ADR-040 D8, добавлены в 01.8c): тонкий spawn-entry (frontmatter `name`/`description`/`tools`/`model`) + указатель на полный хендбук в `agents/<role>/` (profile · system-prompt · tools-allowlist · workflows · checklists — единый источник истины). Конформность spawn-entry ↔ хендбук проверяет `scripts/autonomy/check_subagents.py` (CI-гейт `ci-autonomy`). Long-term role memory + handoff persistence — AgentDB через `claude-flow` MCP (ONNX 384-dim embeddings).

---

## Routing table — 11 persistent ролей

| Role | Layer | Mandate | Extends | Model tier | Memory namespace |
|---|---|---|---|---|---|
| **architect** | cross-cutting | Cross-phase invariants, ADR-keeper, escalation arbiter | gsd-planner + adr-architect + custom layer | Opus | `agent-memory:architect` |
| **planner** | cross-cutting | Phase-spec → executable PLAN.md (декомпозит для pipeline) | gsd-planner + sparc-orchestrator | Opus | `agent-memory:planner` |
| **memory-curator** | cross-cutting | Auto-update STATUS / PLACEHOLDERS / risks / gate-fills; archive rotation | fully custom (memory-coordinator base) | Opus | `agent-memory:memory-curator` |
| **designer** | implementation | Claude Design wrapper — генерит UI mocks/screens из `ui-spec:` | gsd-ui-researcher + UI Designer + Claude Design integration | Opus | `agent-memory:designer` |
| **frontend-implementer** | implementation | designer-output → React + TanStack + shadcn + Tailwind v4 код | gsd-executor + Frontend Developer + Senior Developer | Opus | `agent-memory:frontend-implementer` |
| **backend-implementer** | implementation | Phase-spec backend tasks → Python + FastAPI + Pydantic-AI код | gsd-executor + backend-dev + Backend Architect | Opus | `agent-memory:backend-implementer` |
| **reviewer-frontend** | quality gate | Tokens-compliance, accessibility AA, inventory-conformance | gsd-ui-checker + gsd-ui-auditor + Accessibility Auditor | Opus | `agent-memory:reviewer-frontend` |
| **reviewer-backend** | quality gate | Code / API / DB / migrations review | code-reviewer + Code Reviewer + custom composite | Opus | `agent-memory:reviewer-backend` |
| **reviewer-security** | quality gate | OWASP, secrets, DLP, dependency-scan | security-auditor + Security Engineer + security-architect | Opus | `agent-memory:reviewer-security` |
| **verifier** | quality gate | Runs acceptance criteria как тесты, gates merge | gsd-verifier + production-validator | Opus | `agent-memory:verifier` |
| **evaluator** | quality gate | LLM-as-judge для vertical-prompts golden-dataset | fully custom (gsd-nyquist-auditor base) | Opus | `agent-memory:evaluator` |

### Non-persistent роли (spawned per phase)

`vertical-prompt-author`, `mcp-builder`, `devops-implementer`, `golden-dataset-curator` — поднимаются под конкретный phase, не держат persistent namespace, не входят в routing-table выше. Profile-файлы создаются точечно под нужный phase в Milestone C+.

---

## Pipeline templates

Конкретные YAML-шаблоны лежат в `agents/_shared/pipeline-templates/`. Планировщик (planner role) выбирает шаблон под характер phase'а:

| Template | Когда применяется | Состав |
|---|---|---|
| **backend-feature.yaml** | Phase касается только backend (новый endpoint, migration, MCP integration) | `planner → backend-implementer → reviewer-backend ∥ reviewer-security → verifier → memory-curator → founder` |
| **frontend-feature.yaml** | Phase касается только frontend (новый screen, компонент, refactor TanStack route) | `planner → designer → frontend-implementer → reviewer-frontend ∥ reviewer-security → verifier → memory-curator → founder` |
| **full-stack-feature.yaml** | Phase затрагивает оба слоя (новая фича e2e) | `planner → (designer → frontend-implementer) ∥ backend-implementer → reviewers (frontend, backend, security — параллельно) → verifier → memory-curator → founder` |

Все три шаблона совпадают с pipeline-канвой из [ADR-023 §3](../.planning/decisions/ADR-023-ai-team-runtime.md). Handoff между ролями — CloudEvents 1.0 envelope (schema: `agents/_shared/handoff-schema.json`).

---

## Global rules — cross-cutting invariants

Эти правила действуют для ВСЕХ ролей и pipeline'ов. Нарушение = блокирующий review-flag.

1. **Primary tier — Opus.** Все 11 persistent ролей spawning'аются на Opus per [ADR-023 §1](../.planning/decisions/ADR-023-ai-team-runtime.md). Tier-1 fallback на Sonnet возможен только когда `agents/_shared/cost-budget.yaml` явно разрешает (по типу задачи / времени суток / per-role cap). Решение о fallback принимает planner на этапе декомпозиции, фиксирует в PLAN.md.

2. **Stagnation kill-switch — 30 минут.** Любой агент, не показавший progress (commit / file-write / status-update) за 30 минут wall-clock — автоматически останавливается per [ADR-015 §5](../.planning/decisions/ADR-015-ai-dev-process.md). Контекст сохраняется в `phase-state:<phase-id>` namespace, founder получает notification.

3. **Founder = final approver для tier 3+ PR.** Per [P-INIT-3](../.planning/_meta/GRILL-DECISIONS-ORIION.md#3-policy-decisions-cross-session-stable) и [ADR-027 §5](../.planning/decisions/ADR-027-solo-ai-git-pr-workflow.md). CI green + AI reviewers approved — необходимо, но НЕ достаточно. AI-агенты не имеют merge prerogative. Tier 1-2 могут auto/skim-merge'иться, tier 3+ требует explicit founder approve.

4. **Handoff format — CloudEvents 1.0.** Любая передача артефакта между ролями (planner→implementer, implementer→reviewer, reviewer→verifier) идёт через event envelope, валидируемый по `agents/_shared/handoff-schema.json`. Типы событий следуют namespace `tech.oriion.<domain>.<action>.<version>` (например `tech.oriion.design.mock.v1`).

5. **Atomic AI commits.** Каждый logical step (одна табличка, один endpoint, один компонент) = один commit per [ADR-027 §1](../.planning/decisions/ADR-027-solo-ai-git-pr-workflow.md). Pre-merge rebase делает founder, не AI. Commit message follows tier-table format (`Pipeline-role:` обязательное поле).

6. **Memory persistence.** Каждая роль держит persistent state в своём `agent-memory:<role>` namespace. При context-overflow роль возобновляется из namespace + STATUS.md без потери знаний (см. [ADR-023 §7](../.planning/decisions/ADR-023-ai-team-runtime.md)).

7. **Tools allowlist per role — two layers.** Каждая роль имеет `tools-allowlist.md`. **Coarse layer (harness-enforced):** спавнабельный `agents/<role>.md` объявляет `tools:` — Claude Code реально ограничивает роль этим набором. **Fine layer (behaviorally-enforced):** path/sub-command-скоуп (например reviewer-security пишет ТОЛЬКО в `revisions/`, verifier — только test-runners) **нельзя** выразить во frontmatter — он держится системным промптом роли + review/tripwire-бэкстопом, а не capability-гейтом. Известный gap (01.8c SECURE-аудит P2): роль под prompt-injection формально имеет coarse `Write/Bash`; компенсирующий **PreToolUse-хук**, форсящий documented allowlist, — follow-up (хуки ставит founder). `check_subagents.py` проверяет наличие/конформность spawn-entry, НЕ enforce-скоуп. Попытка выйти за allowlist = немедленный stop + handoff к security-reviewer.

8. **Cost numbers — только в `cost-budget.yaml`.** Per [P-AUDIT-1](../.planning/_meta/GRILL-DECISIONS-ORIION.md#3-policy-decisions-cross-session-stable) экономические числа НЕ живут в ADR / phase-spec / system-prompts. Только в `agents/_shared/cost-budget.yaml`, под founder control.

---

## References

- [ADR-023](../.planning/decisions/ADR-023-ai-team-runtime.md) — authoritative source для ролей, layers, namespaces, runtime
- [ADR-027](../.planning/decisions/ADR-027-solo-ai-git-pr-workflow.md) — Git/PR tier-table, commit format, founder approver policy
- [ADR-015](../.planning/decisions/ADR-015-ai-dev-process.md) — operational hygiene, kill-switch, CI-gates
- [ADR-024](../.planning/decisions/ADR-024-bounded-context-contracts.md) — bounded-context contracts, naming (`agent_archetype_id`)
- [ADR-025](../.planning/decisions/ADR-025-wave-gate-format.md) — acceptance-gate format
- [ADR-026](../.planning/decisions/ADR-026-vertical-expertise-pipeline.md) — vertical-expertise pipeline (evaluator + vertical-prompt-author)
- [GRILL-DECISIONS-ORIION.md](../.planning/_meta/GRILL-DECISIONS-ORIION.md) — DECISION-3 / 5 / 8 / 10 + policy decisions
- [`agents/_shared/cost-budget.yaml`](./agents/_shared/cost-budget.yaml) — founder-controlled per-role caps + Sonnet fallback rules (R-31 mitigation; created in Milestone B.2)
- [`agents/_shared/handoff-schema.json`](./agents/_shared/handoff-schema.json) — CloudEvents 1.0 schema для inter-role handoff (Milestone B.2)
