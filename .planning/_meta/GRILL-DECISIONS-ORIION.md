---
title: GRILL-DECISIONS-ORIION
description: Registry of deep-grill sessions for project Oriion — each session locks fundamental architectural/strategic decisions through founder + Claude Opus long-form dialogue
type: meta-registry
status: living document
last-updated: 2026-05-14
last-session: 4
---

# GRILL-DECISIONS — Oriion Registry

> Регистр глубинных грилл-сессий проекта **Oriion**. Каждая сессия = единичный point-in-time, в котором founder + Claude Opus вместе докручивают одну архитектурную/стратегическую тему до зафиксированных решений. Этот файл — **living document**, append-only для новых сессий, editable только для inventory/status таблиц.
>
> **Как пользоваться:**
> - **Перед началом новой Milestone-сессии:** читаем последние записи в §1 + cross-session policies в §3 + статус в §4.
> - **После завершения работ по Milestone:** добавляем запись в §1, обновляем §4 inventory.
> - **Полные историчные тексты** сессий сохраняются verbatim в §5.

---

## §1 Session log (newest first)

| # | Date | Type | Topic | Outcome | Commit |
|---|---|---|---|---|---|
| 4 | 2026-05-14 | Milestone C planning grill | UI-design policy shift (designer = DS-keeper, primary = ui-ux-pro-max) + Milestone C scope lock + execution plan (5 stacked PR + audit) | 10 grill-decisions C-D1..C-D10 locked + policy P-DESIGN-1 added + UI playbook rewrite + scope split C vs D | [PR #TBD](https://github.com/mrflxxxme/oriion/pulls) (C.1 in flight) |
| 3 | 2026-05-13 | Post-Milestone-B audit | Cross-PR consistency + ADR compliance + strategic readiness | 2 critical issues fixed via B.5 + 4 grill-decisions locked + policy P-AUDIT-3 added | [PR #N TBD](https://github.com/mrflxxxme/oriion/pull/TBD) |
| 2 | 2026-05-13 | Audit follow-up | Milestone A consistency check | Cost-policy cleanup, R-20/R-30 split, Phase 00.5 column rename | [PR #2 d1f41d3](https://github.com/mrflxxxme/oriion/pull/2) |
| 1 | 2026-05-13 | Initial deep-grill | 11 fundamental decisions (team / contracts / gates / vertical-expertise / Git) | 10 ADR + R-29 closed + R-31 added + catalog update | [PR #2 c78c381](https://github.com/mrflxxxme/oriion/pull/2) |

---

## §2 Session detail (newest first)

### Session 4 — Milestone C planning grill (2026-05-14, post-Milestone-B-merged-PR-#10)

**Trigger:** founder request post-Milestone-B-merge: «Прочти `.planning/_meta/GRILL-DECISIONS-ORIION.md`, составь план выполнения задач для проработки Milestone C, согласуй со мной, закрепи в сессии и давай сделаем это!» — invoked via `/anthropic-skills:grill-me`.

**Method:** Founder + Claude Opus (grill-me skill) walked the decision tree branch-by-branch. 3 parallel Explore agents collected baseline state (Wave 0 phases readiness, 4 Light role current detail, contracts + tools + UI readiness). 9 questions resolved via AskUserQuestion. Plan written to plan-file + ExitPlanMode → approved.

**Strategic decisions (C-D1..C-D10):**

| Q | Topic | Decision | Rationale |
|---|---|---|---|
| **C-D1** | Milestone C scope | **Full Session 3 Q4 verbatim** — все 4 Light → Medium upgrade incl. `evaluator`. | Evaluator не в feature-pipeline templates, но должен быть ready без блокировки future vertical-prompts phase. |
| **C-D2** | Phase 00.7 scope | **Functional skeleton end-to-end** (auth register/login + cell-list/create + task-submit form + SSE task-result view). Покрывает Wave 0→1 gate `internal_demo.passed=true`. | Shell-only недостаточен для demo; Full-Wave-0-UI пересоп ломает minimal-C принцип. |
| **C-D3** | UI-design tool primacy | **Policy shift:** designer = DS-keeper, primary tool = **`ui-ux-pro-max` skill** invoked via Skill tool inside Claude Code. Claude Design = fallback для Wave 1+ high-fidelity polish (hero / marketing / illustration-heavy). | Founder direction — DS-ownership внутри Claude Code agent для consistency + tighter feedback loop, не external service dependency. |
| **C-D4** | Policy formalization route | **Session 4 GRILL entry + UI playbook revision** (no ADR-revision yet). ADR-026 update — opt-in if future drift requires it. | Faster path; ADR revision не required если grill + playbook + memory cover the policy surface fully. |
| **C-D5** | PR structure | **5 stacked PRs layered** + 1 audit: C.1 policy → C.2 roles → C.3 phases 00.1-00.3 → C.4 phases 00.4-00.6 → C.5 phase 00.7 → C.6 audit fixes. | Milestone B pattern (4 stacked PR + B.5) сработал — повторяем. Clean rollback granularity per layer; founder review per layer. |
| **C-D6** | B-level inline depth | **Hybrid per P-INIT-1 + P-INIT-2:** cross-link к DRAFT-READY contracts (iam/multitenancy/rbac/agents/tasks/llm-gateway), inline только для phase-specific endpoints/tables не covered shared contracts, actual function signatures + actual pytest/vitest test snippets, ui-spec section обязательна для frontend phases. | Maximum-inline нарушает P-INIT-2 + drift risk. Minimum (pseudocode) не testable. Hybrid даёт detеrminacy без duplication. |
| **C-D7** | Light → Medium role upgrade depth | **Full parity с Medium baseline** (~250 lines system-prompt + 3-5 workflows + 2-3 checklists per role). | Workable-minimum потребует second-pass, экономия мнимая. Ready для Phase 00.7 без блокировки. |
| **C-D8** | Phase 00.7 placement | **∥ 00.6, оба после 00.5.** Frontend skeleton зависит от 00.2 (auth endpoints) + 00.5 (task SSE endpoints); 00.6 не блокирует frontend. | Параллелизация frontend ∥ observability экономит ~1 неделя на критическом пути. |
| **C-D9** | UI policy artifact handling | **Rename** `_meta/ui/CLAUDE-DESIGN-PROMPTS.md` → **`UI-DESIGN-PLAYBOOK.md`** + full content rewrite. Git rename preservит history. | Имя должно отражать ui-ux-pro-max primacy; edit-in-place вводит в заблуждение. |
| **C-D10** | Audit step finale | **C.6 = post-merge consistency audit + fixes** (3 parallel Explore agents → cross-PR consistency / policy compliance / strategic readiness). Findings → Session 5 GRILL entry + §4 inventory update. | Pattern B.5 нашёл 2 critical issues — risk-mitigation перед Phase 00.1 execution. |

**Files modified в C.1 (commit TBD после push):**

- `.planning/_meta/GRILL-DECISIONS-ORIION.md` — Session 4 entry + P-DESIGN-1 policy + §4 inventory update (this commit)
- `.planning/_meta/ui/CLAUDE-DESIGN-PROMPTS.md` → renamed `UI-DESIGN-PLAYBOOK.md` (git rename) + full rewrite (Claude Design primary → ui-ux-pro-max primary, designer = DS-keeper mandate, fallback section §7)
- `.planning/_meta/ui/component-inventory.md` — references update (line 455)
- `.planning/_meta/ui/REVIEW-CHECKLIST.md` — references update (line 251)

**Verified correct (no changes needed):**

- `.planning/_meta/ui/design-tokens.md` — нет references к CLAUDE-DESIGN-PROMPTS.md
- 11 ролей в `.claude/agents/` — structure intact; designer/frontend-implementer/reviewer-frontend/evaluator placeholder readiness confirmed (~40-46 lines system-prompt vs Medium baseline ~175)
- 6 DRAFT-READY contracts (iam/multitenancy/rbac/agents/tasks/llm-gateway) ready для cross-link в B-level phase-specs
- 4 SKELETON contracts (billing/mcp/artifacts/memory) — inline-minimum policy zafiksirovaна

**Forward-looking (Milestones C.2-C.6):**

- C.2 (`feature/milestone-c-2-role-upgrade` base C.1): 4 role full-parity upgrade (~1440 LOC), pipeline-template `frontend-feature.yaml` + `full-stack-feature.yaml` updates per C-D3
- C.3 (base C.2): phase-specs 00.1+00.2+00.3 B-level revision (~700 LOC)
- C.4 (base C.3): phase-specs 00.4+00.5+00.6 B-level revision (~900 LOC)
- C.5 (base C.4): NEW phase 00.7 frontend skeleton spec (~400 LOC) + PHASES.md + README.md updates
- C.6 (base C.5 merged): audit fixes + Session 5 GRILL entry + §4 inventory move Milestone C → ✅ Done

---

### Session 3 — Post-Milestone-B consistency audit (2026-05-13, post-PR-#4-#7-open)

**Trigger:** founder request post-Milestone-B: «проведи дополнительное исследование на целостность, отсутствие пробелов/противоречий внутри собранных PR, а также их достаточность и соответствие моим целям в проекте. Хочу убедиться что всё готово без ошибок к переходу на следующий этап».

**Method:** 3 параллельных Explore-агента просканировали Milestone B (4 PR, 152 файла):
- (a) Cross-PR internal consistency (handoff event-types, role naming, contract FK refs, cost-budget consistency, gate-threshold ↔ verifier-checklist alignment, WB-Seller coordinator ↔ contracts API mapping, naming compliance, OpenAPI/JSON Schema validity)
- (b) ADR + grill-decisions + policy compliance (ADR-023..027 all sections, P-AUDIT-1/2, P-INIT-1..5, §4 inventory delivery)
- (c) Strategic readiness (Phase 00.1 readiness, Wave 0 critical path, Milestone C scope-split, cost-budget realism для Wave 1+, founder goal alignment)

**Critical findings:**

| ID | Finding | Resolution (B.5) |
|---|---|---|
| **C1** | `handoff-schema.json` определял 10 `$defs` event-types, но 11 `handoff-templates.md` ссылались на 36 unique events → **26 missing schema definitions**. Escalation/cross-cutting events (conflict.escalation, agent.stagnated, audit.report, grill.decision, phase.stuck, plan.ui_phase, etc) эмитились бы без validation в Phase 00.1+. | Extend handoff-schema.json с 26 missing `$defs` — все inferred из handoff-templates references. → **Q1 grill decision**. |
| **C2** | WB-Seller `prompts/coordinator.md` `tools_allowed:` использовал slugs (`tasks.create_step`, `memory.cells_search`) не совпадающие с actual REST operationIds (`createTask`, `searchCellMemory`) в `_meta/contracts/*/api.yaml`. Coordinator emit'ил бы invalid tool calls в Phase 00.5. | Создать `_meta/tools/registry.md` — single source-of-truth для всех tool-slugs (REST operationIds + AgentDB MCP names + built-in tools). Update coordinator.md tools_allowed на registry-conformant slugs. Reviewer-backend проверяет conformance. → **Q2 grill decision**. |

**Non-critical findings (deferred to Milestone C/D):**
- Coordinator.md body не упоминает registry — added via B.5
- 4 Light roles (designer / frontend-implementer / reviewer-frontend / evaluator) могут потребовать upgrade к Medium перед Phase 00.7 — deferred к Milestone C trigger

**Strategic decisions (Q3-Q4 grill):**

| Q | Topic | Decision | Rationale |
|---|---|---|---|
| **Q3** | Cost-budget Wave 1+ scaling | **Decouple dev_team + user_production budgets** в cost-budget.yaml. dev_team = $500/mo (current cap для AI-team internal work). user_production = dormant до Wave 1, founder sets caps перед wave-1-to-2 gate. Separate telemetry partitions. | Wave 1+ frontend builds + user-cells executing tasks через LLM gateway создаст confusing signal если оба budget'а смешаны. Decouple даёт clean burn-rate dashboards (dev vs production). |
| **Q4** | Milestone C scope | **Minimal C** — только Wave-0-sprint blockers: Phase 00.1-00.6 B-level revision (P-INIT-1) + Phase 00.7 spec. Verticals naporneniya (40-60 files) + meta-cleanup + handbook + ADR-004/016 + 4 Light→Medium upgrade — **deferred к Milestone D** после Wave 0→1 gate retro. | Faster feedback cycle до Phase 00.1 execution. Откладываемое НЕ исчезает — становится Milestone D после Wave 0 internal demo. |

**Verified correct (audit confirmed):**

- 11 ролей в `.claude/agents/` exact match с ADR-023 §1 (canonical slugs)
- All 11 roles имеют 7 mandatory файлов (profile/system-prompt/workflows/tools-allowlist/handoff-templates/memory + checklists/) per ADR-023 §4
- All 10 bounded contexts в `_meta/contracts/` exist с 4 mandatory файлами per ADR-024 §2-3
- All 5 wave-N-to-N+1 gates compliant с ADR-025 §1 frontmatter schema (status=PENDING, hard_thresholds verbatim match)
- WB-Seller vertical structure compliant с ADR-026 §2 (8 top-level files + prompts/ + golden-dataset/)
- DECISION-11 frontmatter contract соблюдён в всех 3 prompts (coordinator + researcher + listing_writer)
- P-AUDIT-1 (no $ numbers в ADR/contracts/gates) — zero violations
- P-AUDIT-2 (deprecated terms) — все hits в negative-form guard-comments only
- P-INIT-3 (founder = tier 3+ approver) — закреплено в `.claude/AGENTS.md` global rules
- P-INIT-4 (anti-hallucination Level B) — `_meta/verticals/wb-seller/REVIEW-CHECKLIST.md` includes source-citation + founder-review + evaluator gate + 90-day re-verification
- P-INIT-5 (solo founder + 11 AI) — нет multi-FTE legacy references
- §4 «🔜 Milestone B» inventory delivered 100% (90 + 40 + 15 + 7 = 152 files across 4 PR #4-#7)

**Files modified в B.5 (commit TBD после push):**
- `.claude/agents/_shared/handoff-schema.json` — 10 → 36 $defs
- `.claude/agents/_shared/cost-budget.yaml` — v1 → v2 (split dev_team + user_production)
- `.planning/_meta/tools/registry.md` — NEW (~250 строк tool-slug registry)
- `.planning/_meta/verticals/wb-seller/prompts/coordinator.md` — tools_allowed alignment + registry reference в body

---

### Session 2 — Milestone A consistency audit (2026-05-13, post-PR-#2-c78c381)

**Trigger:** founder request post-Milestone-A: «проведи дополнительное исследование репозитория на предмет полноты, согласованности и соответствия моим решениям и целям после Milestone A. Хочу быть уверен, что фундамент собран корректно без пробелов и ошибок».

**Method:** 4 параллельных Explore-агента просканировали:
- (a) 10 ADR (5 new + 5 revised) internal consistency vs GRILL DECISIONS source-of-truth
- (b) 17 нетронутых ADR vs новый ADR-слой (конфликты, stale terminology)
- (c) phase-spec'ы Wave 0/1 + meta-файлы (PROJECT/STATUS/conventions/glossary/handbook)
- (d) risks/REGISTER.md + roadmap waves + project goals

**Critical findings, closed в той же ветке (commit d1f41d3):**

| ID | Finding | Resolution |
|---|---|---|
| **C1** | Cost math conflict: ADR-015 §5 говорил `per-day per-agent $50`, при 11 agents = $16,500/мес. R-31 / GRILL DECISION-3 target = $200-500/мес. Противоречие в моём же ADR-слое. | Все $-числа удалены из ADR-015 §5 / ADR-023 Consequences / R-31. Numbers живут только в `cost-budget.yaml` (Milestone B) под founder control. → **P-AUDIT-1** в §3. |
| **C2** | R-20 и R-30 описывали один риск разными словами («WB/Ozon/1С/Эльба breaking changes»). | Split mandates: **R-20** = broad RF-API instability (SLA / latency / rate-limit / partial outages, все РФ-API); **R-30** = narrow WB/Ozon contract/schema breakage (code-change cases). Каждая запись получила distinct monitoring metrics. |
| **C3** | Phase 00.5 spec использовал `ui_sprite_archetype` как DB column (4 occurrences) несмотря на ADR-024 объявленное deprecation. AI-агент, имплементирующий по этой spec, материализовал бы deprecated schema. | Replaced 4 occurrences в Phase 00.5 → `agent_archetype_id`. Added ADR-024 в ADR-refs Phase 00.5 с пометкой о deprecation. → **P-AUDIT-2** в §3. |

**Deferred to Milestone C** (traceability, без policy change):

- `PROJECT.md` / `STATUS.md` всё ещё описывают 2.5 FTE, OQ-13/14 как Required blockers — diff с GRILL DECISION-3
- `_meta/conventions.md:33` содержит Next.js `app/` artifact; tier-table дублирует ADR-027
- `_meta/open-questions.md`: OQ-13/14/15/16 ещё открыты с deadline'ом «До Phase 00.1»
- `agent-handbook/02-DELEGATION.md` — старые 6 ролей вместо 11 из ADR-023
- `agent-handbook/05-PR-WORKFLOW.md` — inline tier-table вместо cross-ref на ADR-027
- `_meta/glossary.md` — содержит `ui_sprite_archetype`
- ADR-004 + ADR-016 — `ui_sprite_archetype` в живом SQL (deprecated footnoted в ADR-024, но термин в самих файлах не выкорчеван)
- `roadmap/wave-1-core-mvp/README.md` — acceptance metrics (10-15 friends, 75% task success) не совпадают с ADR-025 (NPS≥30, pass_rate≥0.9)
- `roadmap/wave-0-foundation/PHASES.md` — AI-velocity numbers absent (timeline всё ещё базируется на 2.5 FTE × 15 дней)
- Pre-existing $-numbers в R-14 / R-16 (pixel-art бюджет / BYOK pricing) — отдельное founder decision needed

**Verified correct (audit confirmed):**

- 11 ролей в ADR-023 = 11 ролей в DECISION-3 (exact match имён + mandate'ов)
- Wave 0→1 … Wave 4→5 hard thresholds в ADR-025 = thresholds в DECISION-9
- Vertical frontmatter contract в ADR-026 = поля в DECISION-11
- 10 bounded contexts в ADR-024 = 10 contexts в DECISION-7
- Tier-table в ADR-027 = tier-table в DECISION-10 (incl. «Founder = always final approver tier 3+»)
- Three-way ADR boundary (ADR-015 revised / ADR-023 / ADR-027) чистая, no overlap
- Naming `agent_archetype_id` / `agent_archetypes` / `system_roles` единообразно во всех 10 ADR
- Нет циркулярных source-of-truth ссылок (только integration cross-refs)

---

### Session 1 — Initial deep-grill (2026-05-13)

**Trigger:** founder + Claude Opus глубинный диалог post-team-realignment (2.5 FTE → 1 founder + 11 persistent Opus AI-агентов).

**Output:** 11 фундаментальных решений зафиксированы. Полный transcript — §5.1.

**Summary table:**

| # | DECISION | Implementation ADR |
|---|---|---|
| 1 | Phase-spec Wave 0/1 = B-level (inline OpenAPI/DDL/signatures/tests) | Phase revise → Milestone C |
| 2 | Wave 0+1 B-level, Wave 2-5 direction + gate | ADR-025 (gate format) |
| 3 | 11 persistent Opus-ролей + pipeline-per-phase | ADR-023 |
| 4 | Design System B → C → D эволюционно | Milestone B: `_meta/ui/` |
| 5 | `.claude/agents/<role>/` modular split (7 sub-files per role) | ADR-023 §4 |
| 6 | Vertical-expertise Pattern D (AI-baseline + founder edit + friends-loop) | ADR-026 |
| 7 | Schema-contracts bounded-context split (10 contexts в `_meta/contracts/`) | ADR-024 |
| 8 | Runtime = Claude Code Task tool + AgentDB | ADR-023 §6-7 |
| 9 | Acceptance-gate format (YAML frontmatter + Markdown body) | ADR-025 |
| 10 | Phase-branch + atomic AI commits + selective rebase | ADR-027 |
| 11 | Anti-hallucination Level B → C (founder/evaluator → friends-loop) | ADR-026 §3-4 |

**Outcome:** Milestone A executed в PR #2 commit `c78c381`:
- 5 new ADR (ADR-023 / 024 / 025 / 026 / 027)
- 5 revised ADR (ADR-001 / 007 / 010 / 015 / 021)
- `decisions/README.md` catalog (22 → 27 ADR)
- R-29 closed (founder vertical expertise resolves R-29)
- R-31 added (AI-cost overrun open, owner=Founder)

---

## §3 Policy decisions (cross-session, stable)

Зафиксированные policy decisions, действующие независимо от конкретной сессии. Изменение policy = новая grill-сессия + явный override.

| ID | Source | Policy |
|---|---|---|
| **P-AUDIT-1** | Session 2 | **Экономические числа** (cost caps, budgets, financial targets, MRR thresholds, pricing) — НЕ live в ADR / risks-register / phase-spec'ах. Founder discretion only via `.claude/agents/_shared/cost-budget.yaml` (Milestone B artefact). ADR могут ссылаться на существование `cost-budget.yaml` как механизма, но не на конкретные числа. |
| **P-AUDIT-2** | Session 2 | Когда ADR объявляет термин/column/API deprecated, phase-spec'ы с этим термином патчатся **в той же PR** где объявлена deprecation. Не deferred в follow-up milestone — иначе AI-агент материализует deprecated artifact. |
| **P-AUDIT-3** | Session 3 | **Tool-naming registry-conformance.** Любой `.claude/agents/*/tools-allowlist.md` ИЛИ `_meta/verticals/<slug>/prompts/*.md` `tools_allowed:` field MUST reference только slugs из `_meta/tools/registry.md`. Reviewer-backend проверяет conformance перед PR approval. Новый tool = registry-PR-update с justification + role-allowlist + cross-link к contract OR MCP doc. CI check (future Phase 00.1 deliverable) автоматизирует validation. |
| **P-AUDIT-4** | Session 3 | **Cost-budget structure separation.** `.claude/agents/_shared/cost-budget.yaml` MUST разделять `dev_team` (AI-team internal work) и `user_production` (user-cells через LLM gateway) с separate kill-switches, separate telemetry partitions, separate review thresholds. Founder задаёт `user_production.*` numbers перед wave-1-to-2 gate (когда friends start generating real user-traffic cost). dev_team baseline = $500/mo unless explicit override. |
| **P-DESIGN-1** | Session 4 | **Designer-role = design-system keeper. Primary UI-generation tool = `ui-ux-pro-max` skill** (invoked via Skill tool inside Claude Code session). Claude Design (external) = **fallback only** для Wave 1+ high-fidelity hero / marketing / illustration-heavy surfaces, validated via §7 of `_meta/ui/UI-DESIGN-PLAYBOOK.md`. Designer owns `_meta/ui/design-tokens.md` + `_meta/ui/component-inventory.md` + `_meta/ui/UI-DESIGN-PLAYBOOK.md` + co-owns `_meta/ui/REVIEW-CHECKLIST.md` (with reviewer-frontend). Any DS change flows through designer + PR; additive = LGTM solo, modifying = architect consult, removing = 1-wave deprecation cycle. **Supersedes** DECISION-4 implementation references к Claude Design (DECISION-4 strategic intent intact; tool changes). ADR-026 update — opt-in if future drift. |
| **P-INIT-1** | Session 1 (DECISION-1) | Phase-spec'ы Wave 0/1 — **B-level**: inline OpenAPI 3.1 stubs + inline DDL + file-tree diagram + key function signatures (Python+TS) + example test cases (1 unit + 1 integration минимум) + acceptance criteria привязаны к testable checks + `ui-spec:` секция (если phase touches frontend). Wave 2-5 = direction-only до соответствующего acceptance-gate. |
| **P-INIT-2** | Session 1 (DECISION-7) | **Authoritative spec layer** = `_meta/contracts/<bounded-context>/`. Phase-spec'ы импортируют через cross-link (`## Dependencies → Contracts: [iam](../_meta/contracts/iam/)`), не дублируют DDL/OpenAPI. Backend `src/<context>/` — implementation layer, conform'ит контракту. |
| **P-INIT-3** | Session 1 (DECISION-10) | **Founder = always final approver для tier 3+** (per ADR-027 tier-table). AI-агенты не имеют merge prerogative. CI green + AI reviewers approved — необходимо, но не достаточно. |
| **P-INIT-4** | Session 1 (DECISION-11) | Vertical-prompt content (`_meta/verticals/<slug>/prompts/<role>.md`) — source-citation в каждом factual claim (URL + accessed-date) + founder-review checklist + evaluator gate (≥75% golden + 100% adversarial probes) + 90-day re-verification cycle. Wave 1+: friend-loop (3-5 ICP-friends × 5 задач, ≥80% ✅). |
| **P-INIT-5** | Session 1 (DECISION-3) | **Team model:** solo founder + 11 persistent Opus AI-агентов + non-persistent роли spawned per phase. OQ-13/14/15/16 (hiring) → `closed (N/A)` в Milestone C. R-29 закрывается через founder personal vertical expertise. |

---

## §4 Inventory — Done / Pending

### ✅ Done (Milestone A — PR #2)

- 5 new ADR (ADR-023 AI-team runtime / ADR-024 bounded-context contracts / ADR-025 gate format / ADR-026 vertical-expertise / ADR-027 Git-PR workflow)
- 5 revised ADR (ADR-001 / 007 / 010 / 015 / 021)
- `decisions/README.md` catalog updated 22 → 27
- `risks/REGISTER.md`: R-29 closed, R-31 added, R-20/R-30 mandate-split
- Phase 00.5 — column rename `ui_sprite_archetype` → `agent_archetype_id`
- Policy decisions zafiksirovaны в §3

### ✅ Done (Milestone B — PR #4-#7 + B.5)

**4 stacked PR с branch-tree base'ами (per Session 3 Q2 grill decision):**

- **B.1 [#4](https://github.com/mrflxxxme/oriion/pull/4):** `.claude/AGENTS.md` + 11 role-dirs (Medium × 7 / Light × 4) + `_shared/` (handoff-schema + cost-budget + 3 pipeline-templates) — 90 файлов / +8295 LOC
- **B.2 [#5](https://github.com/mrflxxxme/oriion/pull/5):** `_meta/contracts/<context>/` × 10 contexts × 4 mandatory files (iam/multitenancy/rbac/llm-gateway/agents/tasks DRAFT-READY + billing/mcp/artifacts/memory SKELETON) — 40 файлов / +4848 LOC
- **B.3 [#6](https://github.com/mrflxxxme/oriion/pull/6):** `_meta/ui/` × 4 (nordic-warm tokens + 18-component inventory + Claude Design prompts + review checklist) + `_meta/verticals/wb-seller/` × 11 (8 DRAFT + 3 prompts с coordinator full + researcher/listing_writer skeleton + golden-dataset README) — 15 файлов / +2187 LOC
- **B.4 [#7](https://github.com/mrflxxxme/oriion/pull/7):** `gates/_schema/gate.schema.json` + `_template.md` + 5 wave-N-to-N+1.md (all DRAFT с заполненными hard_thresholds из ADR-025 §1, status=PENDING) — 7 файлов / +955 LOC
- **B.5 [#TBD]:** Session 3 audit fixes — handoff-schema extension (10→36 $defs) + `_meta/tools/registry.md` + cost-budget v2 (dev_team / user_production split per P-AUDIT-4) + coordinator.md tool-slug alignment per P-AUDIT-3 + this GRILL-DECISIONS Session 3 entry

**Cumulative Milestone B:** 152 + B.5 файлов across 5 PRs. Foundation для Phase 00.1+ готова.

### 🔜 Milestone B (next session — structural skeletons)

**Pre-session context dump:** этот файл + `[STATUS.md](../STATUS.md)` + `[decisions/README.md](../decisions/README.md)` + ADR-023/024/025/026.

Скоуп Milestone B:

1. **`.claude/AGENTS.md`** — entry-point + routing-table + global rules
2. **`.claude/agents/<role>/`** × 11 ролей (per ADR-023 §1):
   - architect, planner, memory-curator (cross-cutting)
   - designer, frontend-implementer, backend-implementer (implementation)
   - reviewer-frontend, reviewer-backend, reviewer-security, verifier, evaluator (quality gates)
   - Каждая роль = 6-8 файлов: `profile.md`, `system-prompt.md`, `workflows.md`, `tools-allowlist.md`, `checklists/<task-type>.md`, `handoff-templates.md`, `memory.md` (per ADR-023 §4)
3. **`.claude/agents/_shared/`:**
   - `pipeline-templates/` × 3 YAML (backend-feature, frontend-feature, full-stack-feature)
   - `handoff-schema.json` (CloudEvents 1.0 compatible)
   - **`cost-budget.yaml`** ← R-31 mitigation owner; numbers задаёт founder
4. **`_meta/contracts/<context>/`** × 10 contexts (per ADR-024 §1): iam, multitenancy, rbac, billing, llm-gateway, mcp, agents, tasks, artifacts, memory. Каждый = `schema.sql` + `api.yaml` + `events.yaml` + `README.md`.
5. **`_meta/ui/`** × 4 файла (per DECISION-4): `design-tokens.md` (nordic-warm темп. палитра), `component-inventory.md` (15-20 shadcn-based), `CLAUDE-DESIGN-PROMPTS.md`, `REVIEW-CHECKLIST.md`
6. **`_meta/verticals/wb-seller/`** × ~10 файлов (per ADR-026 §2): README, domain-glossary, workflow-dag, `prompts/{coordinator,researcher,listing_writer}.md`, `golden-dataset/` (README + tasks placeholder), REVIEW-CHECKLIST, kpis, changelog
7. **`gates/_schema/gate.schema.json`** + **`gates/_template.md`** (per ADR-025 §1)

### 🟧 Milestone C — In flight (planned Session 4 / 2026-05-14)

Scope confirmed per Session 4 grill-decisions C-D1..C-D10. 5 stacked PRs + 1 audit:

**C.1 — Policy shift + UI playbook revision (~250 LOC) — IN FLIGHT**
- Session 4 GRILL entry (this §1+§2+§3) + P-DESIGN-1 policy added
- `_meta/ui/CLAUDE-DESIGN-PROMPTS.md` → rename `UI-DESIGN-PLAYBOOK.md` + full rewrite (ui-ux-pro-max primacy + designer-as-DS-keeper mandate + Claude Design §7 fallback)
- Cross-refs updated в `_meta/ui/component-inventory.md` + `_meta/ui/REVIEW-CHECKLIST.md`

**C.2 — 4 Light → Medium role upgrade (~1440 LOC)**
- `.claude/agents/{designer,frontend-implementer,reviewer-frontend,evaluator}/` full-parity upgrade (~250 lines system-prompt + 3-5 workflows + 2-3 checklists each)
- `reviewer-frontend` + `evaluator` get NEW `workflows.md` (currently missing)
- `.claude/agents/_shared/pipeline-templates/{frontend-feature,full-stack-feature}.yaml` — design step description aligned с ui-ux-pro-max (C-D3)

**C.3 — Phase B-level revision: 00.1 + 00.2 + 00.3 (~700 LOC)**
- Hybrid B-level per C-D6: cross-link к DRAFT-READY contracts, inline phase-specific only, actual signatures + actual test snippets

**C.4 — Phase B-level revision: 00.4 + 00.5 + 00.6 (~900 LOC)**
- Same hybrid policy; 00.5 ui-spec minimal (task-progress SSE contract used by 00.7)

**C.5 — NEW Phase 00.7 frontend skeleton (~400 LOC)**
- Functional skeleton end-to-end (auth + cell + task-submit + SSE result) per C-D2
- ∥ 00.6 после 00.5 per C-D8
- `PHASES.md` + `README.md` dependency-graph updates

**C.6 — Post-merge consistency audit + fixes (~150 LOC fix budget)**
- 3 parallel Explore agents (cross-PR consistency / policy compliance / strategic readiness)
- Findings → Session 5 GRILL entry + §4 inventory move к ✅ Done

### 🟦 Milestone D — Deferred (post-Wave-0 retro)

**Vertical naporneniya:**
- Phase 00.5 vertical-tasks для `_meta/verticals/wb-seller/` (WB-Seller 40-60 files + 30 golden-dataset tasks per ADR-026 §1)
- 4 additional verticals scaffolds (Marketing / TG-Creator / Accounting / SMB-Sales — Wave 1+)

**Meta-файлы cleanup:**
- `PROJECT.md` — team section solo + 11 AI (P-INIT-5)
- `STATUS.md` — убрать OQ-13/14/15/16 из active blockers; new Phase 00.7 row
- `_meta/open-questions.md` — close OQ-13/14/15/16 with `status: closed (N/A: solo + AI model)` per P-INIT-5
- `_meta/conventions.md:33` — replace `app/` → `frontend/src/routes/` (TanStack); tier-table → cross-ref ADR-027
- `_meta/glossary.md` — add `agent_archetype_id` / `agent_archetypes` / `system_roles`; remove `ui_sprite_archetype`
- `_meta/stack.md` — verify frontend structure совпадает с ADR-001 (revised)
- `agent-handbook/02-DELEGATION.md` — переписать под 11 ролей из ADR-023
- `agent-handbook/05-PR-WORKFLOW.md` — убрать inline tier-table, cross-ref на ADR-027
- `agent-handbook/07-AI-TEAM-PIPELINE.md` — NEW: pipeline template + handoff schema + failure handling
- `agent-handbook/00-START-HERE.md` — pipeline-flow mention + ссылка на `.claude/AGENTS.md`

**ADR backlog (deferred high-severity):**
- ADR-004 + ADR-016 — replace `ui_sprite_archetype` в live SQL examples (per P-AUDIT-2)

**Roadmap:**
- `roadmap/wave-1-core-mvp/README.md` — acceptance metrics align с ADR-025 (NPS≥30, pass_rate≥0.9)
- `roadmap/wave-0-foundation/PHASES.md` — AI-velocity timeline пересчёт (под solo + 11 AI vs 2.5 FTE × 15 дней)
- `roadmap/wave-0-foundation/README.md` — capacity → AI-velocity terms

**Risks:**
- R-NN gaps: формализовать что R-13 / R-15 были — restored или explicit «merged into R-NN» entries

### 📌 Out-of-scope (отдельные founder decisions, не привязаны к Milestone)

- **Economic numbers cleanup** для pre-existing R-14 ($3-5K pixel-art бюджет) и R-16 ($9/mo BYOK pricing) — per P-AUDIT-1 эти числа не должны быть в risks. Но pre-existing, требует явного founder go.
- **GA business metrics** в `PROJECT.md` (500 paying customers, MRR 3M ₽ к Wave 3) — per P-AUDIT-1 экономика out-of-scope. Но это product/business targets, не cost-cap; founder может оставить.

---

## §5 Original session contexts (preserved verbatim)

### §5.1 Initial grill — 2026-05-13 (full original text)

Ниже — полный исходный текст файла `GRILL-DECISIONS-2026-05-13.md` от 2026-05-13, переименованного в этот registry. Сохраняется для traceability source-of-truth: новые ADR в Milestone A генерились по этому тексту. Bootstrap-инструкции в конце (Execution plan, Sign-off checklist) теперь устарели — заменены §1-§4 этого файла.

---

> **status: APPROVED — ready for bootstrap-session** (на момент 2026-05-13; статус устарел после исполнения Milestone A)
> **supersedes:** none
> **informs:** ADR-023, ADR-024, ADR-025, ADR-026, ADR-027 (created in PR #2); ADR-001, ADR-007, ADR-010, ADR-015, ADR-021 (revised in PR #2)
> **context:** solo founder + 11 persistent Opus AI-agents (post-grill realignment)

#### Контекст (для следующей сессии — теперь historical)

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

#### DECISION-1: Уровень детализации phase-spec'ов = B (implementation-ready)

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

#### DECISION-2: Scope = Wave 0+1 B-level, Wave 2-5 direction + gate

**Принято:** Hybrid C (из вопроса 2).
- Wave 0 (6 phases) — B-level сейчас (bootstrap)
- Wave 1 (10 phase-directions) — B-level сейчас (bootstrap)
- Wave 2-5 — остаются direction-level
- Переход Wave N → Wave N+1 управляется через **acceptance-gate** (см. DECISION-9), AI-планировщик генерит Wave N+1 spec'и автономно из gate-data

**Rationale:** Wave 2+ сильно зависит от Wave 1 learnings (TTFV, friend-feedback, какие verticals взлетят). Детализация Wave 2-5 сейчас была бы спекулятивной. Wave 0-1 архитектурно зафиксированы в ADR — риск переделок минимален.

---

#### DECISION-3: Team model = B+C — pipeline-per-phase + 11 persistent Opus agents

**Принято:** 11 persistent ролей на Opus (full quality budget):

| # | Role | Layer | Mandate | Base (reuse) |
|---|---|---|---|---|
| 1 | **architect** | Cross-cutting | Cross-phase invariants, ADR-keeper, escalation arbiter | gsd-planner + adr-architect + custom |
| 2 | **planner** | Cross-cutting | Phase-spec → executable PLAN.md (decomposes for pipeline) | gsd-planner + sparc-orchestrator |
| 3 | **memory-curator** | Cross-cutting | Auto-update STATUS / PLACEHOLDERS / risks / gate-fills; archive rotation | fully custom (memory-coordinator base) |
| 4 | **designer** | Implementation | Claude Design wrapper — generates UI mocks/screens from `ui-spec:` | gsd-ui-researcher + UI Designer + Claude Design integration |
| 5 | **frontend-implementer** | Implementation | designer-output → React+TanStack+shadcn code | gsd-executor + Frontend Developer + Senior Developer |
| 6 | **backend-implementer** | Implementation | Phase-spec backend tasks → Python+FastAPI+Pydantic code | gsd-executor + backend-dev + Backend Architect |
| 7 | **reviewer-frontend** | Quality gate | Tokens-compliance, accessibility AA, inventory-conformance | gsd-ui-checker + gsd-ui-auditor + Accessibility Auditor |
| 8 | **reviewer-backend** | Quality gate | Code/API/DB/migrations review | code-reviewer + Code Reviewer + custom composite |
| 9 | **reviewer-security** | Quality gate | OWASP / secrets / DLP / dependency-scan | security-auditor + Security Engineer + security-architect |
| 10 | **verifier** | Quality gate | Runs acceptance criteria as tests, gates merge | gsd-verifier + production-validator |
| 11 | **evaluator** | Quality gate | LLM-as-judge для vertical-prompts golden-dataset | fully custom (gsd-nyquist-auditor base) |

**Non-persistent (spawned per phase):** `vertical-prompt-author`, `mcp-builder`, `devops-implementer`, `golden-dataset-curator`.

**Pipeline template:** `planner → (designer → frontend-impl) ∥ backend-impl → reviewers (parallel) → verifier → memory-curator → Founder approve`.

**Cost-control:** [исходный текст содержал конкретные числа budget — удалены post-audit per P-AUDIT-1; cap policy → `cost-budget.yaml` под founder control; mitigation owner = R-31].

---

#### DECISION-4: Design System = B→C→D эволюционно

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

#### DECISION-5: `.claude/agents/<role>/` структура = C (modular split)

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
        └── cost-budget.yaml               # founder-controlled cap policy (R-31 mitigation; numbers выносятся сюда per P-AUDIT-1)
```

**Rationale:** JIT-loading нужного sub-файла, лёгкое обновление single dimension, совпадает с принципом JIT context-loading из `agent-handbook/01-CONTEXT-LOADING.md`.

---

#### DECISION-6: Vertical-expertise = D (AI-baseline + friends-loop) + founder=expert all 5

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

#### DECISION-7: Schema-contracts = C (bounded-context split)

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

#### DECISION-8: Runtime-инфраструктура = C (Claude Code Task-tool + AgentDB bridge)

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

#### DECISION-9: Acceptance-gate Wave→Wave = C (YAML frontmatter + Markdown body)

**Принято:** Format C с конкретной структурой. Файлы: `.planning/gates/wave-N-to-N+1.md` + schema в `.planning/gates/_schema/gate.schema.json`.

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

#### DECISION-10: Git/PR workflow = C (phase-branch + atomic AI commits + selective rebase)

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

#### DECISION-11: Anti-hallucination для vertical-prompt-author = B/W0 → C/W1+

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

> **Note:** Inventory + Execution plan + Sign-off checklist разделы исходного GRILL-DECISIONS-2026-05-13 → перенесены в §4 этого файла (живой inventory) и заменены результатами Milestone A в §1-§2. Историческая bootstrap-инструкция: открыть новую Claude Opus сессию, сказать «Прочти `.planning/_meta/GRILL-DECISIONS-ORIION.md`, выполни Milestone B per §4».

🎯 **Документация переведена в shared understanding. Готова к ready-to-build bootstrap (Milestone A done, B/C — следующие сессии).**
