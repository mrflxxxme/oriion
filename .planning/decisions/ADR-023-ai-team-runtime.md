# ADR-023: AI-team runtime — 11 persistent Opus-ролей + `.claude/agents/` структура + AgentDB bridge

- **Status:** Accepted

## Decision

Покрывает [GRILL-DECISIONS-2026-05-13](../_meta/GRILL-DECISIONS-2026-05-13.md) DECISION-3 (team-модель), DECISION-5 (folder-структура), DECISION-8 (spawning runtime). Определяет «КТО эти агенты» и «КАК они запускаются». Тематики Git/PR workflow и operational hygiene вынесены в ADR-027 и ADR-015 (revised) соответственно.

### 1. Команда — 1 founder + 11 persistent Opus-ролей

Все 11 ролей работают на Opus с full quality budget. Три слоя:

**Cross-cutting (3):**

| Роль | Mandate | Base reuse |
|---|---|---|
| **architect** | Cross-phase invariants, ADR-keeper, escalation arbiter | gsd-planner + adr-architect + custom layer |
| **planner** | Phase-spec → executable PLAN.md (декомпозит для pipeline) | gsd-planner + sparc-orchestrator |
| **memory-curator** | Auto-update STATUS / PLACEHOLDERS / risks / gate-fills; archive rotation | fully custom (memory-coordinator base) |

**Implementation (3):**

| Роль | Mandate | Base reuse |
|---|---|---|
| **designer** | Claude Design wrapper — генерит UI mocks/screens из `ui-spec:` | gsd-ui-researcher + UI Designer + Claude Design integration |
| **frontend-implementer** | designer-output → React + TanStack + shadcn + Tailwind v4 код | gsd-executor + Frontend Developer + Senior Developer |
| **backend-implementer** | Phase-spec backend tasks → Python + FastAPI + Pydantic-AI код | gsd-executor + backend-dev + Backend Architect |

**Quality gates (5):**

| Роль | Mandate | Base reuse |
|---|---|---|
| **reviewer-frontend** | Tokens-compliance, accessibility AA, inventory-conformance | gsd-ui-checker + gsd-ui-auditor + Accessibility Auditor |
| **reviewer-backend** | Code/API/DB/migrations review | code-reviewer + Code Reviewer + custom composite |
| **reviewer-security** | OWASP, secrets, DLP, dependency-scan | security-auditor + Security Engineer + security-architect |
| **verifier** | Runs acceptance criteria как тесты, gates merge | gsd-verifier + production-validator |
| **evaluator** | LLM-as-judge для vertical-prompts golden-dataset | fully custom (gsd-nyquist-auditor base) |

### 2. Non-persistent роли — spawned per phase

`vertical-prompt-author`, `mcp-builder`, `devops-implementer`, `golden-dataset-curator`. Эти роли поднимаются под конкретные phase'ы и не держат persistent memory namespace.

### 3. Pipeline-шаблон

```
planner
  → (designer → frontend-implementer) ∥ backend-implementer
  → reviewers (frontend, backend, security — параллельно)
  → verifier
  → memory-curator
  → Founder approve (per tier-table в ADR-027)
```

Конкретные YAML-шаблоны pipeline'ов лежат в `.claude/agents/_shared/pipeline-templates/` — `backend-feature.yaml`, `frontend-feature.yaml`, `full-stack-feature.yaml`. Detailed контракты — Milestone B.

### 4. `.claude/agents/<role>/` structure (modular split)

Каждая роль имеет каталог с следующими файлами:

```
.claude/agents/<role>/
├── profile.md              # who, when, model-tier (Opus), memory-namespace, base-agent-reused
├── system-prompt.md        # actual system-prompt at spawn-time
├── workflows.md            # typical task playbooks
├── tools-allowlist.md      # tools allowed to this role (security)
├── checklists/
│   └── <task-type>.md      # per-task-type checklists (pr-review.md, security-audit.md, ...)
├── handoff-templates.md    # CloudEvents 1.0 envelopes для handoff к next роли в pipeline
└── memory.md               # AgentDB namespace + что persists между сессиями
```

JIT-loading: каждый sub-файл загружается только когда роль реально нуждается в нём, экономя tokens (см. agent-handbook/01-CONTEXT-LOADING.md).

Конкретные файлы создаются в Milestone B.

### 5. `_shared/` артефакты

```
.claude/agents/_shared/
├── pipeline-templates/
│   ├── backend-feature.yaml       # planner → backend-impl → reviewers → verifier
│   ├── frontend-feature.yaml      # planner → designer → frontend-impl → reviewers → verifier
│   └── full-stack-feature.yaml    # параллельные backend + frontend tracks
├── handoff-schema.json            # JSON schema для handoff-сообщений (CloudEvents 1.0 compatible)
└── cost-budget.yaml               # per-role monthly cap + Sonnet fallback rules (R-31 mitigation)
```

Конкретные содержимые — Milestone B.

### 6. Spawning runtime — Claude Code Task tool + AgentDB bridge

- **Spawning:** native Claude Code `Task` tool с `subagent_type=<our-role>`, где `<our-role>` определён в `.claude/agents/<role>/profile.md` через extends GSD или Anthropic base-agent.
- **Memory:** AgentDB через `claude-flow` MCP. ONNX 384-dim embeddings (all-MiniLM-L6-v2). DiskANN или HNSW vector search в зависимости от scale.
- **GSD reuse:** команды `/gsd:plan-phase`, `/gsd:execute-phase`, `/gsd:verify-work`, `/gsd:ship` работают «из коробки» — структура `.planning/` совпадает с GSD-ожиданиями.

### 7. AgentDB namespaces

| Namespace | Назначение |
|---|---|
| `agent-memory:<role>` | Long-term role memory (decisions, patterns, lessons learned) |
| `phase-state:<phase-id>` | Current phase progress + handoff messages между ролями |
| `domain-knowledge:<vertical>` | Vertical-template golden context (см. ADR-026) |
| `adr-patterns` | Pattern-search для архитектурных решений (используется architect) |

### 8. Founder-in-the-loop UX

Два режима утверждения:
- **(a) GitHub PR review** — для финального merge tier 3+ (см. ADR-027 tier-table).
- **(b) Interactive в Claude Code** — агенты возвращают artifact → founder отвечает `merge` / `revise X` / `abort` в той же сессии.

## Consequences

- **Reuse heavy:** 5-6 ролей реализуются как thin wrapper над GSD/Anthropic skill agents (~50-100 строк profile + system-prompt). 3-4 роли = полностью custom (memory-curator, evaluator, reviewer-security composite, architect deep layer) — ~200 строк каждая. Estimated effort на Milestone B: ~1 рабочий день.
- **Cost под контролем:** Opus × 11 ролей × frequent invocations = ~$200-500/мес целевой budget. Mitigation owner — [R-31](../risks/REGISTER.md#r-31-ai-cost-overrun-under-11-opus-persistent-team). Конкретные cap'ы — в `_shared/cost-budget.yaml` (Milestone B).
- **Routing tier-based:** routine задачи (tier 1-2 per ADR-027) могут fallback на Sonnet через `cost-budget.yaml`. High-stakes задачи (tier 3+) — всегда Opus.
- **Memory persistence:** AgentDB обеспечивает cross-session continuity. При context-overflow роль возобновляется из своего namespace + STATUS.md без потери знаний.
- **No merge prerogative для AI:** агенты возвращают artifact + approval status; финальный merge — за founder (см. ADR-027).

## Links

- [GRILL-DECISIONS-2026-05-13](../_meta/GRILL-DECISIONS-2026-05-13.md) — DECISION-3, DECISION-5, DECISION-8
- [ADR-015](./ADR-015-ai-dev-process.md) — operational hygiene (isolation, observability, kill-switch)
- [ADR-027](./ADR-027-solo-ai-git-pr-workflow.md) — Git/PR workflow + tier-table
- [ADR-024](./ADR-024-bounded-context-contracts.md) — bounded-context contracts (используется ролями)
- [ADR-026](./ADR-026-vertical-expertise-pipeline.md) — vertical-expertise pipeline (роль evaluator + vertical-prompt-author)
- Risk: [R-31](../risks/REGISTER.md) — AI-cost overrun
- Memory infra: claude-flow MCP, AgentDB, ONNX embeddings
