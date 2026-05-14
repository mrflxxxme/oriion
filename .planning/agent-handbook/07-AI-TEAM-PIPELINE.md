# 07-AI-TEAM-PIPELINE — Pipeline mechanics for 11 persistent Opus AI-agents

> **Цель:** Single source-of-truth для **как** работает AI-team pipeline. Реализационные детали 11 ролей лежат в [`.claude/agents/<role>/`](../../.claude/agents/); этот документ описывает **runtime, handoff, failure, и cost mechanics** между ними per [ADR-023](../decisions/ADR-023-ai-team-runtime.md), [ADR-025](../decisions/ADR-025-gate-format.md), [ADR-027](../decisions/ADR-027-solo-ai-git-pr-workflow.md).

> **Аудитория:** AI-agent в любой role (architect, planner, implementer, reviewer, verifier, memory-curator) — этот файл даёт mental model для координации внутри pipeline.

> **Связанные документы:**
> - [`02-DELEGATION.md`](./02-DELEGATION.md) — **когда** invoke какую роль
> - [`04-HANDOFF.md`](./04-HANDOFF.md) — handoff-notes template (legacy + role-to-role compat)
> - [`05-PR-WORKFLOW.md`](./05-PR-WORKFLOW.md) — PR mechanics после verifier sign-off

---

## 1. Pipeline overview

11 persistent Opus AI-agents (per [ADR-023 §1](../decisions/ADR-023-ai-team-runtime.md), [DECISION-3](../decisions/ADR-028-policies-registry.md#decision-3)) делятся на 3 слоя:

- **Cross-cutting (3):** `architect` (ADR-keeper) / `planner` (phase → PLAN.md) / `memory-curator` (state-sync + archive)
- **Implementation (3):** `designer` (DS-keeper + UI mocks) / `frontend-implementer` (React+TanStack) / `backend-implementer` (Python+FastAPI+Pydantic)
- **Quality gates (5):** `reviewer-frontend` / `reviewer-backend` / `reviewer-security` / `verifier` (acceptance gate) / `evaluator` (LLM-as-judge for vertical prompts)

**Canonical pipeline** для feature phase:

```
[Phase-spec ready]
        │
        ▼
  planner (decomposes phase → PLAN.md)
        │
        ├──► designer (if `ui-spec:` present)
        │           │
        │           ▼
        │     frontend-implementer
        │           │
        ├──► backend-implementer (in parallel ∥)
        │           │
        ├───────────┴──────────┐
        ▼                      ▼
  reviewer-frontend ∥ reviewer-backend ∥ reviewer-security
        │            (3 reviewers parallel)
        ▼
  verifier (runs acceptance criteria as tests)
        │
        ▼
  memory-curator (state updates + STATUS / risks / gate-fills)
        │
        ▼
  Founder approve (tier 3+ per [P-INIT-3](../decisions/ADR-028-policies-registry.md#policies-canonical-home))
        │
        ▼
  PR merge → main
```

Per [DECISION-3](../decisions/ADR-028-policies-registry.md#decision-3): **Founder = always final approver tier 3+**. AI-агенты не имеют merge prerogative.

---

## 2. Pipeline templates (YAML orchestration)

3 reusable templates в [`.claude/agents/_shared/pipeline-templates/`](../../.claude/agents/_shared/pipeline-templates/):

| Template | Когда применяется | Sequence |
|---|---|---|
| `backend-feature.yaml` | Phase touches только backend (API, DB, migrations) | planner → backend-implementer → (reviewer-backend ∥ reviewer-security) → verifier → memory-curator |
| `frontend-feature.yaml` | Phase touches только frontend (UI, routing, components) | planner → designer (ui-ux-pro-max primary per [P-DESIGN-1](../decisions/ADR-028-policies-registry.md#policies-canonical-home)) → frontend-implementer → reviewer-frontend → verifier → memory-curator |
| `full-stack-feature.yaml` | Phase touches both layers (auth, billing, vertical-runtime) | planner → fork: (designer → frontend-impl) ∥ (backend-impl) → converge: (reviewer-frontend ∥ reviewer-backend ∥ reviewer-security) → verifier → memory-curator |

**Template selection:** planner читает phase-spec frontmatter + `ui-spec:` presence → выбирает template → invokes implementers per template DAG.

**Custom pipeline:** для non-feature work (research, ADR drafting, post-mortems) — planner создаёт ad-hoc invocation chain в PLAN.md, не используя YAML template.

---

## 3. Handoff contract

**Format:** CloudEvents 1.0 spec per [ADR-024 §3](../decisions/ADR-024-bounded-context-contracts.md) — все handoffs между ролями = structured events.

**Schema:** [`.claude/agents/_shared/handoff-schema.json`](../../.claude/agents/_shared/handoff-schema.json) — **36 $defs** (per Session 3 B.5 audit fix) покрывающие full event-types vocabulary:

- `task.*` — 9 events (started / step_started / step_token / step_completed / delegation_started / delegation_completed / completed / cancelled / failed)
- `phase.*` — phase-lifecycle events
- `review.*` — reviewer feedback emit
- `gate.*` — verifier + gate-fill events
- `conflict.escalation` / `agent.stagnated` / `audit.report` / `grill.decision` / `phase.stuck` — escalation events

**Mandatory fields в каждом handoff event:**

```yaml
specversion: "1.0"
type: oriion.<bounded-context>.<event-name>.v1
source: agent://<role>/<instance-id>
id: <uuid>
time: <ISO-8601>
datacontenttype: application/json
phase: <phase-id>
data:
  # role-specific payload per schema $def
```

**Per-role handoff templates** в `<role>/handoff-templates.md` — конкретные payload shapes для каждой role-to-role transition (e.g. `planner → backend-implementer`, `backend-implementer → reviewer-backend`).

---

## 4. Failure handling — revision loop

Per [DECISION-10](../decisions/ADR-028-policies-registry.md#decision-10):

```
reviewer | verifier обнаруживает issue
        │
        ▼
  creates revisions/<phase>-<reviewer>.md
        │
        ▼
  planner — перепланирует tasks (incremental delta, не full re-plan)
        │
        ▼
  implementer — фиксит per revisions/ feedback
        │
        ▼
  re-review (back к reviewer or verifier)
        │
        ├── ✅ passed → continue pipeline
        └── ❌ failed → loop (max 3 cycles)
                            │
                            ▼
                      После 3 cycles — эскалация Founder
                      (handoff event: oriion.escalation.iteration-exhausted.v1)
```

**Cycle counter** хранится в `phase-state:<phase-id>` namespace (memory-curator). Founder может явно override max-cycles если задача требует deeper iteration.

**Escalation выходы:**
- **Reviewer disagrees с implementer's fix** — emit `oriion.escalation.review-deadlock.v1` → architect arbitrates
- **Verifier finds acceptance gap не в scope phase-spec** — emit `oriion.escalation.scope-creep.v1` → planner + Founder decide
- **Security-reviewer finds Tier-4 issue в Tier-3 PR** — emit `oriion.escalation.security-upgrade.v1` → re-tier + Founder explicit approve

---

## 5. Anti-drift mechanisms

AI-team — multiple parallel agents с risk of incoherence. Anti-drift guards:

### 5.1 Phase-state memory namespace

Per [ADR-023 §7](../decisions/ADR-023-ai-team-runtime.md): every phase имеет namespace `phase-state:<phase-id>` в AgentDB (claude-flow MCP). Содержит:
- Current task progress (queue / in-progress / done)
- Handoff messages history (last N events)
- Cycle counter (revision loops)
- Cost-spent counter (per cost-budget.yaml integration)
- Active blockers + escalation flags

**All роли** читают этот namespace при invoke. Все updates emit через memory-curator (single-writer pattern, prevents race).

### 5.2 Checkpoint protocol

После каждой role-handoff:
1. Receiving role читает emitted event
2. Validates payload против `handoff-schema.json` $def
3. Если valid → starts work; если invalid → emit `oriion.handoff.schema-violation.v1` к sender
4. После work completion → emit completion event + invokes memory-curator для state update

**Checkpoint frequency:** per-task default; per-step optional для long-running implementations (>30 min wall-clock).

### 5.3 ADR conformance check

Каждый implementation handoff содержит `adr-refs: [ADR-XXX, ADR-YYY]` field. reviewer-backend / reviewer-frontend проверяют что код не нарушает referenced ADRs. Architect эскалирован если новый ADR нужен.

### 5.4 Tools-allowlist conformance per P-AUDIT-3

`reviewer-backend` validates что `tools_allowed:` в любом prompt (`.claude/agents/*/tools-allowlist.md` ИЛИ `verticals/*/prompts/*.md`) — все slugs из [`tools/registry.md`](../tools/registry.md). Non-conformant = block PR (per [P-AUDIT-3](../decisions/ADR-028-policies-registry.md#policies-canonical-home)).

---

## 6. Cost-control hooks

Per [P-AUDIT-4](../decisions/ADR-028-policies-registry.md#policies-canonical-home): cost-budget separated в [`.claude/agents/_shared/cost-budget.yaml`](../../.claude/agents/_shared/cost-budget.yaml) на 2 partition:

- **`dev_team`** — AI-team internal work (planning, implementation, review, verification). Wave 0-3 dev cap = founder-controlled.
- **`user_production`** — user-cells executing tasks через LLM gateway (Wave 1+). Dormant до Wave 1; founder sets caps перед wave-1-to-2 gate.

**Per-role hooks:**

- Каждый role tracks LLM tokens spent в `phase-state:<phase-id>.cost.<role>.tokens`
- memory-curator aggregates → `phase-state:<phase-id>.cost.total`
- При превышении soft-cap (per cost-budget.yaml) → emit `oriion.cost.soft-cap-hit.v1` → planner switches к fallback model (claude-sonnet-4-6) для non-critical steps
- При превышении hard-cap → emit `oriion.cost.hard-cap-hit.v1` → pipeline suspended → Founder explicit approve для continue

**Per-task hooks (Wave 1+ user-production):**
- Single user-task end-to-end LLM cost ≤ ₽5 (Wave 0 internal) / ≤ 10% от paid price per action (Wave 1+)
- Excess triggers cost-budget.yaml `user_production.kill_switch` per cell

---

## 7. CI integration

После memory-curator's PR creation (per pipeline finish), CI gates fire (per [conventions.md §CI gates](../_meta/conventions.md)):

```
1. Lint (ruff, eslint)
2. Type-check (mypy strict, tsc strict)
3. Unit tests + coverage (≥70% new / ≥85% security-critical)
4. Integration tests
5. Security: Semgrep / Bandit / gitleaks / pip-audit / npm audit
6. SBOM (Syft) + vuln scan (Grype)
7. License scan (no GPL/AGPL)
8. Container scan (Trivy)
9. Migration safety (squawk)
10. Golden dataset regression (если role prompt changed) — invokes evaluator
11. Performance benchmark (для critical endpoints)
```

**CI failure handling:**
- Tier 1 (auto-merge) — CI fail = no merge, ping memory-curator → opens revision loop
- Tier 2+ — CI fail = block, reviewer-backend investigates root cause, эскалирует к planner если scope issue
- Tier 4 — CI fail на security-related check = emergency stop, reviewer-security investigates

**P-AUDIT-3 CI check (future Phase 00.1 deliverable):** automated tools-allowlist conformance validation на каждом PR. Currently manual (reviewer-backend).

---

## 8. Founder approval points

Per [ADR-027 §tier-table](../decisions/ADR-027-solo-ai-git-pr-workflow.md) + [P-INIT-3](../decisions/ADR-028-policies-registry.md#policies-canonical-home):

| Tier | Founder action | When |
|---|---|---|
| **1** | Auto-merge if CI green | Docs, format, dep-patch |
| **2** | Skim diff, ack | Tests, refactors, copy |
| **3** | **Explicit approve** required | New endpoint, component, feature |
| **4** | **Explicit approve** + ADR-link required | Architecture, security, billing, migrations |
| **5** | **Same-session approve** | Hotfix |

**AI-агенты не имеют merge prerogative.** CI green + AI reviewers approved — необходимо, но **не достаточно** для tier 3+.

**Founder-in-the-loop UX patterns:**
- **(a) GitHub UI** — PR review для финального merge (default)
- **(b) Interactive в Claude Code** — pipeline возвращает artifact + summary → Founder говорит «merge / revise X / abort»

**Founder override** для escalations:
- `oriion.escalation.iteration-exhausted.v1` — Founder reviews revision diff, либо continues loop либо abandons phase
- `oriion.escalation.review-deadlock.v1` — Founder arbitrates между reviewer и implementer когда architect-arbitration insufficient
- `oriion.escalation.scope-creep.v1` — Founder decides: expand phase-spec или defer к новой phase
- `oriion.cost.hard-cap-hit.v1` — Founder approves cap-bump или suspends phase

**Founder = единственный source-of-truth для tier 3+ merge.** Этот контракт zafiksirovan в [P-INIT-3](../decisions/ADR-028-policies-registry.md#policies-canonical-home) и не override-яется без новой grill-session.

---

## Cross-references

- **Pipeline overview + role catalog:** [ADR-023 §1-3](../decisions/ADR-023-ai-team-runtime.md)
- **Bounded contexts + naming:** [ADR-024](../decisions/ADR-024-bounded-context-contracts.md)
- **Gate format (Wave-N-to-N+1):** [ADR-025](../decisions/ADR-025-gate-format.md)
- **Vertical-expertise (evaluator gate):** [ADR-026](../decisions/ADR-026-vertical-expertise.md)
- **Git/PR/tier:** [ADR-027](../decisions/ADR-027-solo-ai-git-pr-workflow.md)
- **Policies:** [P-INIT-1..5 + P-AUDIT-1..4 + P-DESIGN-1](../decisions/ADR-028-policies-registry.md#policies-canonical-home)
- **Tool registry:** [`tools/registry.md`](../tools/registry.md)
- **Pipeline YAML templates:** [`.claude/agents/_shared/pipeline-templates/`](../../.claude/agents/_shared/pipeline-templates/)
- **Handoff schema:** [`.claude/agents/_shared/handoff-schema.json`](../../.claude/agents/_shared/handoff-schema.json)
- **Cost budget:** [`.claude/agents/_shared/cost-budget.yaml`](../../.claude/agents/_shared/cost-budget.yaml)
