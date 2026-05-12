---
title: GRILL-DECISIONS-2026-05-13
date: 2026-05-13
status: APPROVED — ready for bootstrap-session
type: meta-decision-record
supersedes: none
informs:
  - ADR-023 (to be created)
  - ADR-024 (to be created)
  - ADR-025 (to be created)
  - ADR-026 (to be created)
  - ADR-027 (to be created)
  - ADR-001, ADR-007, ADR-015 (to be revised)
context: solo founder + 11 persistent Opus AI-agents (post-grill realignment)
---

# GRILL-DECISIONS — 2026-05-13

> **Single source of truth для 11 принятых решений** глубинного интервью 2026-05-13.
> Bootstrap-сессия (следующая Claude Opus сессия) использует этот файл как primary context
> для генерации всех новых ADR, structure, skeletons. После выполнения bootstrap файл архивируется в `archive/`.

## Контекст (для следующей сессии)

**Что произошло:** Founder + Claude Opus провели глубинный грилл репозитория `.planning/` по 11 фундаментальным развилкам. Зафиксировали B-level ready-to-go архитектуру под **solo founder + 11 persistent Opus AI-агентов** (вместо ранее предполагаемой multi-FTE команды).

**Что изменилось vs предыдущее состояние:**
- Команда: 2.5 FTE → 1 founder + 11 AI-agents (все на Opus)
- OQ-13/14/15/16 (hiring) закрываются как N/A
- R-29 закрывается через founder personal operating expertise по всем 5 verticals
- Wave 0 получает новую Phase 00.7 (frontend skeleton via Claude Design)
- Все phase-spec'и переходят на B-level (inline OpenAPI + DDL + signatures)
- Wave 2-5 остаются direction-only до acceptance-gate триггера

**Что не изменилось:**
- Stack (Python+FastAPI+Pydantic-AI / Vite+React+TanStack / DeepSeek+YandexGPT+GigaChat / Yandex Cloud)
- 5 vertical-templates (WB / Marketing / TG-creator / Accounting / SMB-Sales)
- 6 waves roadmap (timing пересмотрен под AI-velocity)
- 22 existing ADR (только 5 revised, остальные intact)

---

## DECISION-1: Уровень детализации phase-spec'ов = B (implementation-ready)

**Принято:** Каждая phase-spec в Wave 0 и Wave 1 содержит:
- Goal (1 sentence) + Dependencies + Tasks list (текущее)
- **inline OpenAPI 3.1 stubs** для endpoint'ов этой phase
- **inline DDL** (CREATE TABLE + индексы + RLS policies) для новых таблиц
- **file-tree diagram** что добавляется/изменяется
- **key function signatures** (Python + TypeScript) для критичных модулей
- **example test cases** (минимум 1 unit + 1 integration в виде кода)
- **acceptance criteria** (текущее, но привязано к testable checks)
- **ADR-refs + Risks** (текущее)
- **`ui-spec:` секция** (если phase touches frontend) — page-layouts + content slots + interaction states

**Rationale:** Без B-level два AI-агента могут принять несовместимые решения по API/schema, ломая interop между phase'ами. B-level даёт detеrminacy contracts при сохранении свободы AI на «как».

**Применимость:** Wave 0 (6 phases) + Wave 1 (10 directions → 10 B-level spec'ов). Wave 2-5 = direction-only (см. DECISION-2).

---

## DECISION-2: Scope = Wave 0+1 B-level, Wave 2-5 direction + gate

**Принято:** Hybrid C (из вопроса 2).
- Wave 0 (6 phases) — B-level сейчас (bootstrap)
- Wave 1 (10 phase-directions) — B-level сейчас (bootstrap)
- Wave 2-5 — остаются direction-level
- Переход Wave N → Wave N+1 управляется через **acceptance-gate** (см. DECISION-9), AI-планировщик генерит Wave N+1 spec'и автономно из gate-data

**Rationale:** Wave 2+ сильно зависит от Wave 1 learnings (TTFV, friend-feedback, какие verticals взлетят). Детализация Wave 2-5 сейчас была бы спекулятивной. Wave 0-1 архитектурно зафиксированы в ADR — риск переделок минимален.

---

## DECISION-3: Team model = B+C — pipeline-per-phase + 11 persistent Opus agents

**Принято:** 11 persistent ролей на Opus (full quality budget):

| # | Role | Layer | Mandate | Base (reuse) |
|---|---|---|---|---|
| 1 | **architect** | Cross-cutting | Cross-phase invariants, ADR-keeper, escalation arbiter | gsd-planner + adr-architect + custom |
| 2 | **planner** | Cross-cutting | Phase-spec → executable PLAN.md (decomposes for pipeline) | gsd-planner + sparc-orchestrator |
| 3 | **memory-curator** | Cross-cutting | Auto-update STATUS / PLACEHOLDERS / risks / gate-fills; archive rotation | **fully custom** (memory-coordinator base) |
| 4 | **designer** | Implementation | Claude Design wrapper — generates UI mocks/screens from `ui-spec:` | gsd-ui-researcher + UI Designer + Claude Design integration |
| 5 | **frontend-implementer** | Implementation | designer-output → React+TanStack+shadcn code | gsd-executor + Frontend Developer + Senior Developer |
| 6 | **backend-implementer** | Implementation | Phase-spec backend tasks → Python+FastAPI+Pydantic code | gsd-executor + backend-dev + Backend Architect |
| 7 | **reviewer-frontend** | Quality gate | Tokens-compliance, accessibility AA, inventory-conformance | gsd-ui-checker + gsd-ui-auditor + Accessibility Auditor |
| 8 | **reviewer-backend** | Quality gate | Code/API/DB/migrations review | code-reviewer + Code Reviewer + custom composite |
| 9 | **reviewer-security** | Quality gate | OWASP / secrets / DLP / dependency-scan | security-auditor + Security Engineer + security-architect |
| 10 | **verifier** | Quality gate | Runs acceptance criteria as tests, gates merge | gsd-verifier + production-validator |
| 11 | **evaluator** | Quality gate | LLM-as-judge для vertical-prompts golden-dataset | **fully custom** (gsd-nyquist-auditor base) |

**Non-persistent (spawned per phase):** `vertical-prompt-author`, `mcp-builder`, `devops-implementer`, `golden-dataset-curator`.

**Pipeline template:** `planner → (designer → frontend-impl) ∥ backend-impl → reviewers (parallel) → verifier → memory-curator → Founder approve`.

**Cost-control:** Opus × 11 ролей × frequent invocations = ~$200-500/мес. Bookmarked как **R-31** в risks-register с mitigation = monthly cap + tier-1 Sonnet fallback для routine tasks.

---

## DECISION-4: Design System = B→C→D эволюционно

**Принято:**

| Wave | Уровень | Артефакты |
|---|---|---|
| Wave 0 | **B** | `_meta/ui/design-tokens.md` (nordic-warm темп. палитра) + `_meta/ui/component-inventory.md` (15-20 shadcn-based компонентов с props/states) |
| Wave 1 | **C** | + `_meta/ui/reference-screens/` (8 экранов, генерим Claude Design в первый раз → фиксируем как reference image attachments) |
| Wave 2 | **D** | После OQ-09 (бренд) → финальные tokens + `frontend/src/components/ui/` как single source + Pixel Department layer (Canvas-герои overlay) |

**Доп. артефакты сейчас:**
- `_meta/ui/CLAUDE-DESIGN-PROMPTS.md` — system-prompt templates для Claude Design (output format: React + TanStack + shadcn + Tailwind v4)
- `_meta/ui/REVIEW-CHECKLIST.md` — checklist для reviewer-frontend (accessibility AA, responsive, tokens-compliance, inventory-compliance, no inline styles)

**`ui-spec:` field в frontend phase-spec'ах:**
```yaml
ui-spec:
  pages:
    - slug: cells-list
      layout: dashboard
      content-slots: [header, sidebar, main-table, empty-state]
      interaction-states: [loading, empty, error, populated]
      a11y-must-have: [keyboard-nav, screen-reader-labels, focus-trap]
  components-used: [Button, Card, Table, EmptyState, Skeleton]
  new-components-needed: []
```

**Темпорарная палитра (Wave 0/1):** `nordic-warm`:
- base: slate-900 (#0f172a)
- surface: slate-800 / slate-100 (light)
- primary: amber-500 (#f59e0b)
- success: emerald-500
- danger: rose-600
- typography: Inter (UI) + JetBrains Mono (code/data)

---

## DECISION-5: `.claude/agents/<role>/` структура = C (modular split)

**Принято:**
```
.claude/
├── AGENTS.md                              # entry-point + routing-table + global rules
└── agents/
    ├── <role>/
    │   ├── profile.md                     # who, when, model-tier (Opus), memory-namespace, base-agent-reused
    │   ├── system-prompt.md               # actual system-prompt at spawn-time
    │   ├── workflows.md                   # typical task playbooks
    │   ├── tools-allowlist.md             # what tools this role can use (security)
    │   ├── checklists/<task-type>.md      # per-task-type checklists (e.g. pr-review.md, security-audit.md)
    │   ├── handoff-templates.md           # how this role hands off to next in pipeline (CloudEvents)
    │   └── memory.md                      # namespace + what persists between sessions
    └── _shared/
        ├── pipeline-templates/            # reusable phase-pipeline YAMLs
        │   ├── backend-feature.yaml       # planner → backend-impl → reviewers → verifier
        │   ├── frontend-feature.yaml      # planner → designer → frontend-impl → reviewers → verifier
        │   └── full-stack-feature.yaml    # parallel backend+frontend tracks
        ├── handoff-schema.json            # JSON schema для handoff-сообщений (CloudEvents 1.0 compatible)
        └── cost-budget.yaml               # per-role monthly cap + Sonnet fallback rules (R-31 mitigation)
```

**Rationale:** JIT-loading нужного sub-файла, лёгкое обновление single dimension, совпадает с принципом JIT context-loading из `agent-handbook/01-CONTEXT-LOADING.md`.

---

## DECISION-6: Vertical-expertise = D (AI-baseline + friends-loop) + founder=expert all 5

**Принято:** Pattern D + structure `_meta/verticals/<slug>/`:
```
.planning/_meta/verticals/<vertical-slug>/
├── README.md              # ICP, JTBD, KPI, primary tasks
├── domain-glossary.md     # термины (FBO, FBS, артикул, выкуп, рейтинг, ...)
├── workflow-dag.md        # как агенты взаимодействуют (Coordinator → Researcher → Writer → ...)
├── prompts/
│   ├── coordinator.md     # полный system-prompt (versioned, SemVer per ADR-010)
│   ├── researcher.md
│   └── <role>.md
├── golden-dataset/
│   ├── README.md          # методология оценки (LLM-as-judge criteria + rubrics)
│   └── tasks/
│       ├── 001-<slug>.md  # task: input + expected-output-shape + rubric per task
│       └── ...            # 30 tasks per vertical (10 easy / 15 medium / 5 hard) для WB-Селлер Wave 0
├── REVIEW-CHECKLIST.md    # founder-review checklist (per DECISION-11)
├── kpis.md                # business-метрики (TTFV, success-rate, NPS)
└── changelog.md           # изменения промптов (для regression-tracking)
```

**Founder = real expert по всем 5 вертикалям** → R-29 закрывается с обоснованием «Founder personal operating expertise», not «AI claim».

**Wave 0 deliverable (WB-Селлер only):** 1 vertical × ~40-60 файлов готовы к Phase 00.5 acceptance.

**Wave 1+ verticals:** AI-baseline → founder edit → friends-loop validation.

---

## DECISION-7: Schema-contracts = C (bounded-context split)

**Принято:**
```
.planning/_meta/contracts/
├── iam/                   # users, sessions, refresh_tokens, oauth_links
│   ├── schema.sql
│   ├── api.yaml           # OpenAPI 3.1
│   ├── events.yaml        # CloudEvents 1.0 spec
│   └── README.md          # invariants + ubiquitous language + ADR/phase refs
├── multitenancy/          # organizations, cells, cell_members, RLS policies
├── rbac/                  # system_roles, permissions, role_assignments
├── billing/               # credit_balances, credit_transactions, pricing_table, tariff_plans
├── llm-gateway/           # byok_keys, llm_provider_config, llm_usage_log
├── mcp/                   # mcp_connections, mcp_tools, mcp_health_log
├── agents/                # agent_archetypes (renamed from sprite-IDs!), team_presets, agent_instances
├── tasks/                 # tasks, task_steps, task_artifacts
├── artifacts/             # yjs_documents, s3_assets (Wave 1)
└── memory/                # cell_memory, role_memory, embeddings (Wave 1)
```

**Naming corrections:**
- `roles_rbac` (system-level) → **`system_roles`**
- `roles_agent` (vertical-level AI roles) → **`agent_archetypes`**
- `sprite-ID` / `ui_sprite_archetype` (Phase 00.5 stale terms) → **`agent_archetype_id`** (FK to `agent_archetypes` table)

**Events format:** CloudEvents 1.0 spec (Python SDK available, future-proof для NATS/Kafka в Wave 4).

**Alembic migrations:** `backend/alembic/versions/<context>/` for analogous isolation.

**Phase-files referencing:** import только нужные context'ы через cross-link, не дублировать DDL.

---

## DECISION-8: Runtime-инфраструктура = C (Claude Code Task-tool + AgentDB bridge)

**Принято:**
- **Spawning:** native Claude Code Task tool с `subagent_type=<our-role>` (где `<our-role>` определён в `.claude/agents/<role>/profile.md` через extends GSD/Anthropic base)
- **Memory:** AgentDB через claude-flow MCP, ONNX 384-dim embeddings, HNSW vector search
- **Bootstrap-парадокс resolution:** Founder + эта сессия (как **bootstrap-session**) генерят первоначальные `.claude/agents/<role>/*` файлы. Reuse heavy:
  - 5-6 ролей = thin wrapper над GSD/Anthropic skill agents (~50-100 строк)
  - 3-4 роли = полностью custom (memory-curator, evaluator, reviewer-security composite, architect-deep-layer) (~200 строк)
  - Estimated effort: ~1 рабочий день

**AgentDB namespaces:**
- `agent-memory:<role>` — long-term role memory (decisions, patterns)
- `phase-state:<phase-id>` — current phase progress + handoff messages
- `domain-knowledge:<vertical>` — vertical-template golden context
- `adr-patterns` — pattern-search для архитектурных решений

**Founder-in-the-loop UX:**
- (a) PR review в GitHub UI для финального merge
- (b) Interactive в Claude Code: агенты возвращают artifact → founder говорит «merge / revise X / abort»

**GSD reuse:** Команды `/gsd:plan-phase`, `/gsd:execute-phase`, `/gsd:verify-work`, `/gsd:ship` работают «из коробки» — `.planning/` структура совпадает.

---

## DECISION-9: Acceptance-gate Wave→Wave = C (YAML frontmatter + Markdown body)

**Принято:** Format C с конкретной структурой (см. вопрос 9 transcript). Файлы: `.planning/gates/wave-N-to-N+1.md` + schema в `.planning/gates/_schema/gate.schema.json`.

**Hard go/no-go gates:**
- Wave 0→1: `internal_demo.passed=true`
- Wave 1→2: `friend_feedback.nps >= 30` AND `acceptance_criteria_pass_rate >= 0.9`
- Wave 2→3: `weekly_registrations >= 100` AND `TTFV_minutes <= 3` AND `conversion >= 0.05`
- Wave 3→4: `paying_customers >= 500` AND `MRR_RUB >= 3_000_000`
- Wave 4→5: `paying_customers >= 2000` AND `MRR_RUB >= 15_000_000`

**Fill protocol:**
- `memory-curator` auto-fills 80% (metrics + deliverables + ADR-delta + risks-delta + capacity-snapshot)
- Founder fills narrative (retro themes, strategic implications, scope-changes) + sets `status: PASSED/BLOCKED`

---

## DECISION-10: Git/PR workflow = C (phase-branch + atomic AI commits + selective rebase)

**Принято:**
- **Branching:** `feature/wave-N-phase-NN.M-<slug>` per phase, AI-агенты atomic commits внутри
- **Pre-merge:** founder делает interactive rebase для 3-5 logical chunks (по необходимости)
- **Merge policy:** tier 1/2 = squash; tier 3/4 = rebase merge (сохраняем pipeline-trail); tier 5 = fast-forward после verifier
- **No merge-commits в main**

**AI commit format:**
```
feat(<bounded-context>): <description>

Phase: <id>
Pipeline-role: <role-name>
Reviewers: <list with approval status>
ADR-refs: <list>

Co-Authored-By: <role-name> (Opus) <role@teamly-ai>
```

**Tier-table re-thought для solo+AI:**
| Tier | Примеры | AI reviewers | Founder action |
|---|---|---|---|
| 1 | Docs, format, dep-patch | — | Auto-merge if CI green |
| 2 | Tests, refactors, copy | 1 (relevant reviewer) | Skim diff, ack |
| 3 | New endpoint, component | 2 (code + security) | Approve |
| 4 | Architecture, security, billing, migrations | 3 (code + security + architect) + ADR-link required | Explicit approve |
| 5 | Hotfix | 1 expedited + verifier full-acceptance | Same-session approve |

**Founder = всегда финальный approver для tier 3+.** AI-агенты не имеют merge prerogative.

**Failure handling:** reviewer создаёт `revisions/<phase>-<reviewer>.md` → planner перепланирует → implementer фиксит → re-review (max 3 цикла, потом эскалация founder).

**Force-push:** AI-агенты имеют `--force-with-lease` ТОЛЬКО на feature-branch. main защищена branch-protection.

**Commit signing:** GPG-sign отложен до Wave 3 (GA-release).

---

## DECISION-11: Anti-hallucination для vertical-prompt-author = B/W0 → C/W1+

**Принято:**

**Wave 0 (founder = expert + evaluator gate):** Level B
- Source-citation требуется в каждом факте (URL + accessed-date)
- Founder-review checklist обязателен перед `status: reviewed`
- Evaluator gate: 30 golden-tasks → ≥75% pass + 5 adversarial probes → 100%
- 90-day re-verification cycle (memory-curator triggers PR)

**Wave 1+ (friend-loop):** Level C
- 3-5 ICP-friends per вертикаль, each runs 5 реальных задач
- ≥80% ✅ rating = `status: locked`
- Negative examples → новые golden-dataset tasks (rolling expansion)
- Comparison oracle (DeepSeek vs YandexGPT vs GigaChat divergence-flag) с Wave 2

**Frontmatter contract** для каждого `_meta/verticals/<vertical>/prompts/<role>.md`:
```yaml
---
role: coordinator
vertical: wb-seller
version: 0.1.0
status: draft | reviewed | promoted | locked
verified-by: [founder-review, evaluator-pass]
verified-at: 2026-05-20
verified-sources:
  - url: ...
    accessed: 2026-05-12
    relevance: ...
golden-dataset-pass-rate: 0.83
adversarial-probes-pass-rate: 1.0
hallucination-flags: []
friend-validation:
  participants: 0
  positive-rate: null
  comments: []
next-verification: 2026-08-13  # +90 days
---
```

---

## Inventory: что создать / обновить / архивировать в bootstrap-session

### Новые ADR (5 шт.)

| ADR | Title | Source decision |
|---|---|---|
| **ADR-023** | AI-team runtime (B+C pipeline + 11 persistent agents + AgentDB bridge) | DECISION-3, DECISION-5, DECISION-8 |
| **ADR-024** | Bounded-context contracts (`_meta/contracts/` structure + naming) | DECISION-7 |
| **ADR-025** | Acceptance-gate format (Wave→Wave transitions) | DECISION-9 |
| **ADR-026** | Vertical-expertise pipeline (D-pattern + anti-hallucination protocol) | DECISION-6, DECISION-11 |
| **ADR-027** | Solo + AI Git/PR workflow (re-thought tier-review) | DECISION-10 |

### Revised existing ADR (5 шт.)

| ADR | Revision |
|---|---|
| **ADR-001** (modular monolith) | + ссылка на `agent_archetypes` rename (was `ui_sprite_archetype`); ссылки на `_meta/contracts/` структуру |
| **ADR-007** (auth) | Owner-семантика → AI-roles (`backend-implementer` + `reviewer-security`) |
| **ADR-010** (role-versioning) | Применяется к `_meta/verticals/<slug>/prompts/*.md`, не к sprite-IDs |
| **ADR-015** (AI-dev process) | Полностью переписать под solo + 11 AI: tier-table из DECISION-10, pipeline-template из DECISION-3, AI-cost cap |
| **ADR-021** (AI-generated pixel pipeline) | Sprite-IDs → `agent_archetype_id` через FK к `_meta/contracts/agents/schema.sql` |

### Новые файлы (planning structure)

```
.planning/
├── _meta/
│   ├── contracts/                                # NEW (DECISION-7)
│   │   ├── README.md                             # entry-point + bounded-context map
│   │   ├── iam/{schema.sql, api.yaml, events.yaml, README.md}
│   │   ├── multitenancy/...
│   │   ├── rbac/...
│   │   ├── billing/...                           # stub for Wave 0, full Wave 1.4
│   │   ├── llm-gateway/...
│   │   ├── mcp/...                               # stub for Wave 0, full Wave 1.10
│   │   ├── agents/...
│   │   ├── tasks/...
│   │   ├── artifacts/...                         # Wave 1 stub
│   │   └── memory/...                            # Wave 1 stub
│   │
│   ├── ui/                                       # NEW (DECISION-4)
│   │   ├── design-tokens.md                      # nordic-warm temp palette
│   │   ├── component-inventory.md                # 15-20 shadcn-based components
│   │   ├── CLAUDE-DESIGN-PROMPTS.md              # system-prompt templates
│   │   └── REVIEW-CHECKLIST.md                   # reviewer-frontend checklist
│   │
│   ├── verticals/                                # NEW (DECISION-6)
│   │   ├── README.md                             # vertical-templates inventory
│   │   └── wb-seller/                            # Wave 0 only
│   │       ├── README.md
│   │       ├── domain-glossary.md
│   │       ├── workflow-dag.md
│   │       ├── prompts/{coordinator,researcher,listing_writer}.md
│   │       ├── golden-dataset/README.md (+ tasks/ — empty for now, filled by vertical-prompt-author + founder)
│   │       ├── REVIEW-CHECKLIST.md
│   │       ├── kpis.md
│   │       └── changelog.md
│   │
│   └── GRILL-DECISIONS-2026-05-13.md             # this file
│
├── gates/                                        # NEW (DECISION-9)
│   ├── _schema/gate.schema.json                  # JSON schema for validation
│   └── _template.md                              # template for new gates
│
└── roadmap/wave-0-foundation/phases/
    └── 00.7-frontend-skeleton.md                 # NEW (DECISION-3 + Q3 follow-up)
```

### Новые файлы (`.claude/`)

```
.claude/
├── AGENTS.md                                     # NEW — entry-point + routing-table
└── agents/
    ├── architect/{profile,system-prompt,workflows,tools-allowlist,handoff-templates,memory}.md + checklists/
    ├── planner/...
    ├── memory-curator/...                        # custom
    ├── designer/...
    ├── frontend-implementer/...
    ├── backend-implementer/...
    ├── reviewer-frontend/...
    ├── reviewer-backend/...
    ├── reviewer-security/...
    ├── verifier/...
    ├── evaluator/...                             # custom
    └── _shared/
        ├── pipeline-templates/{backend-feature,frontend-feature,full-stack-feature}.yaml
        ├── handoff-schema.json                   # CloudEvents 1.0 compatible
        └── cost-budget.yaml                      # R-31 mitigation
```

### Updated existing files

| File | Update |
|---|---|
| `PROJECT.md` | Команда: solo + 11 AI-agents; новая Phase 00.7; new ADRs ref; нейтральная палитра mention |
| `STATUS.md` | Active blockers: убрать OQ-13/14/15/16 как N/A; добавить bootstrap-session as next step |
| `_meta/stack.md` | Frontend structure: `frontend/src/routes/` (TanStack file-based), убрать `app/` (Next.js artifact) |
| `_meta/conventions.md:33` | Frontend structure correction (как выше); Git workflow → ссылка на ADR-027 |
| `_meta/open-questions.md` | OQ-13/14/15/16 → status `closed (N/A: solo + AI model)`; OQ-numbering audit (см. ниже) |
| `agent-handbook/02-DELEGATION.md` | Перечень subagents → 11 persistent + non-persistent; убрать «Senior Backend hire» |
| `agent-handbook/00-START-HERE.md` | Pipeline-flow mention + ссылка на `.claude/AGENTS.md` |
| `agent-handbook/07-AI-TEAM-PIPELINE.md` | **NEW** — pipeline template + handoff schema + failure handling |
| `risks/REGISTER.md` | + R-31 (AI-cost overrun); R-29 closing с founder-expertise обоснованием |
| `roadmap/wave-0-foundation/PHASES.md` | + Phase 00.7 row; renumber total to 26 человеко-дней (но AI-velocity ≠ человеко-дни) |
| `roadmap/wave-0-foundation/README.md` | Owner-семантика → AI-roles; capacity → AI-velocity terms |
| `roadmap/wave-1-core-mvp/PHASES.md` | + конкретизация phase-spec'ов до B-level (10 направлений → 10 spec'ов) |
| Each Wave 0 phase-spec (00.1...00.6) | + inline OpenAPI/DDL/file-tree/signatures/tests; + `pipeline:` поле; + `ui-spec:` (если frontend) |
| `decisions/README.md` | Update ADR catalog (22 → 27) |

### Archived

| File | Destination | Reason |
|---|---|---|
| `archive/READY-TO-BUILD-2026-05-12.md` | already in archive ✓ | reference snapshot, intact |
| `archive/SYNTHESIS-2026-05-12.md` | already in archive ✓ | reference snapshot, intact |
| `_meta/GRILL-DECISIONS-2026-05-13.md` | → `archive/GRILL-DECISIONS-2026-05-13.md` after bootstrap | this file rotates to archive |

---

## Trivial cleanups (no decision needed, memory-curator handles)

1. **OQ numbering audit:** OQ-01, 06-12, 20, 23-24, 27-28 missing. memory-curator scans archive/SYNTHESIS-2026-05-12.md + risks/REGISTER.md → either reconstructs or marks `merged into OQ-X` / `closed (N/A)`. Document audit result in `_meta/open-questions.md` appendix.
2. **`conventions.md:33` Next.js artifact:** replace `app/` → `frontend/src/routes/` (TanStack Router file-based). Same file: line about «1+ human reviewers» → reference ADR-027.
3. **Wave 1 README.md** «команда 2 × full + 0.5 DevOps» → solo + 11 AI rephrasing.
4. **PLACEHOLDERS.md** — добавить новые TBD: `TBD_AGENT_GPG_KEY` (Wave 3+), `TBD_AGENTDB_DAEMON_HOST` (если remote AgentDB).

---

## Execution plan (для bootstrap-session)

Bootstrap-session = новая Claude Opus сессия в свежем context'е. Reads `.planning/_meta/GRILL-DECISIONS-2026-05-13.md` + `.planning/README.md` + `.planning/STATUS.md` (3 файла, ~25 KB context).

**Recommended ordering (~8-12 часов AI-времени, можно частично параллелить):**

1. **Создать 5 новых ADR** (ADR-023...027) — sequential, ~2 часа.
2. **Revise 5 existing ADR** (ADR-001, 007, 010, 015, 021) — sequential, ~1.5 часа.
3. **Создать `.claude/AGENTS.md` + 11 ролевых каталогов** (`.claude/agents/<role>/*`) — 4-6 parallel sub-agents (через Task-tool), ~2 часа wall-clock.
   - Sub-agent A: architect + planner + memory-curator (cross-cutting)
   - Sub-agent B: designer + frontend-implementer + backend-implementer (implementers)
   - Sub-agent C: reviewer-{frontend,backend,security} (reviewers)
   - Sub-agent D: verifier + evaluator (quality gates)
   - Sub-agent E: `_shared/` (pipeline templates + handoff schema + cost budget)
4. **Создать `_meta/contracts/<context>/` skeleton** — parallel sub-agents per bounded-context, ~1.5 часа.
5. **Создать `_meta/ui/` (4 файла)** + `_meta/verticals/wb-seller/` skeleton (10 файлов) — parallel, ~1 час.
6. **Создать Phase 00.7 spec** + revise все Wave 0 phase-spec'ы до B-level (inline OpenAPI/DDL/file-tree) — sequential, ~2 часа.
7. **Создать `gates/_schema/gate.schema.json` + template** — 30 мин.
8. **Update planning meta-files** (PROJECT, STATUS, stack, conventions, glossary, open-questions, agent-handbook, risks, roadmap READMEs) — parallel sub-agents, ~1 час.
9. **Memory-curator trivial cleanups** (OQ-numbering audit, stale-refs fix, PLACEHOLDERS additions) — 30 мин.
10. **Final commit** в feature branch `feature/grill-2026-05-13-apply-decisions`, PR с описанием всех изменений, founder review + merge.

**Total wall-clock estimate:** 1.5-2 рабочих дня для solo + AI-team в interactive mode; 8-12 часов если идти sequentially через Task-tool.

---

## Risks для bootstrap-session

| Risk | Mitigation |
|---|---|
| Bootstrap-сессия теряет context на середине | Этот файл + STATUS + README = self-contained, можно перезапустить с того же шага |
| Параллельные sub-agents создают inconsistent naming | Все используют этот файл как single SOURCE — `system_roles`, `agent_archetypes`, `agent_archetype_id`, etc. явно зафиксированы |
| Conflict между новыми ADR и old phase-spec'ами | Sequential order: сначала ADR'ы (2-3 шага), потом phase-revisions (шаг 6) с ссылками на новые ADR |
| Founder отвлечётся, AI начнёт догадываться | Bootstrap-session работает на DECISION-1...11 только. Любая новая развилка → escalate к founder, не догадываться |
| AgentDB daemon не запущен | Bootstrap-session проверяет `npx @claude-flow/cli@latest daemon start` в шаге 0 |

---

## Sign-off checklist (founder verification после bootstrap)

После выполнения bootstrap-session founder проверяет:

- [ ] Все 5 новых ADR существуют и cross-referenced в `decisions/README.md`
- [ ] `.claude/AGENTS.md` + 11 ролевых каталогов созданы, каждый ~6-8 файлов
- [ ] `_meta/contracts/` 10 bounded-contexts со skeleton-схемами
- [ ] `_meta/ui/` 4 файла + темп. палитра nordic-warm
- [ ] `_meta/verticals/wb-seller/` skeleton готов для vertical-prompt-author
- [ ] Phase 00.7 (frontend skeleton) создан с B-level spec
- [ ] Wave 0 phase-spec'ы (00.1...00.6) обновлены до B-level (inline OpenAPI/DDL)
- [ ] `gates/_schema/gate.schema.json` + template созданы
- [ ] PROJECT/STATUS/stack/conventions/open-questions обновлены
- [ ] R-31 добавлен, R-29 закрыт с founder-expertise обоснованием
- [ ] `STATUS.md` Active blockers: OQ-13/14/15/16 removed (N/A для solo+AI)
- [ ] PR с описанием всех изменений готов к merge
- [ ] Этот файл (GRILL-DECISIONS-2026-05-13.md) перемещён в `archive/`

После всех галочек — `STATUS.md → Wave 0 Phase 00.1 ready to start`.

---

## End of GRILL — handoff to bootstrap-session

Следующее действие: founder открывает новую Claude Opus сессию в этом репозитории, говорит:
> «Прочти `.planning/_meta/GRILL-DECISIONS-2026-05-13.md`, выполни Execution plan, отчитайся sign-off checklist'ом».

Опционально перед этим: founder подтверждает AgentDB daemon работает (`npx @claude-flow/cli@latest daemon start` + `npx @claude-flow/cli@latest doctor --fix`).

🎯 **Документация переведена в шерд-понимание. Готова к ready-to-build bootstrap.**
