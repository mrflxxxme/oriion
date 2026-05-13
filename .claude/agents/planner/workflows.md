# planner — workflows

Три canonical playbook'а. Если задача не ложится — escalate к founder.

---

## Workflow 1 — Phase-spec decomposition (first-pass)

**Trigger:** founder открыл новый phase из roadmap. CloudEvent
`tech.oriion.phase.spec.v1` от founder.

**Inputs:**
- `.planning/roadmap/wave-N-*/phases/NN.M-<slug>.md` (B-level phase-spec)
- `_meta/contracts/<context>/*` для всех контекстов в Dependencies секции
- `decisions/README.md` для verify ADR-refs existence
- `risks/REGISTER.md` для linked risks

**Steps:**

1. **Validate phase-spec is B-level.** Per P-INIT-1 checklist:
   - Goal + Dependencies + Tasks list — присутствуют?
   - Inline OpenAPI 3.1 stubs (если backend tasks) — присутствуют?
   - Inline DDL (если new tables) — присутствует?
   - File-tree diagram — есть?
   - Key function signatures (Python + TS) — есть?
   - ≥1 unit + ≥1 integration test cases — есть?
   - Acceptance criteria привязаны к testable checks?
   - `ui-spec:` секция (если frontend) — есть?

   Любое «нет» — abort, emit `tech.oriion.spec.incomplete.v1` к founder с list missing
   items. НЕ начинай decomposition с incomplete spec — это создаст divergent implementations.

2. **Verify contract references.** Phase-spec должен ссылаться на
   `_meta/contracts/<context>/` через cross-link (P-INIT-2). Если упоминает таблицу или
   endpoint, не присутствующий в contracts — escalate к `architect` (это нужен новый ADR
   и contract update).

3. **Identify pipeline template.** Из `_shared/pipeline-templates/`:
   - Pure backend → `backend-feature.yaml`
   - Pure frontend → `frontend-feature.yaml`
   - Both → `full-stack-feature.yaml` (parallel tracks)
   - Vertical-prompt → special, escalate к founder для spawn `vertical-prompt-author`

4. **Decompose tasks.** Per Decomposition heuristics в system-prompt §A:
   - Каждый endpoint, table, component, test = отдельная task
   - Назначить role per task
   - Identify dependencies (T2 depends on T1 если T2 импортирует T1's output)
   - Group в parallel-groups (independent tasks)
   - Estimate tier per ADR-027 §5

5. **Map acceptance criteria → tests.** Для каждой acceptance criterion из spec — найди
   соответствующий test (existing или to-be-added) и attach verifier check.

6. **Build handoff plan table.** Per pipeline-template — sequence of CloudEvents.

7. **Self-audit per checklist** (`checklists/plan-quality.md`).

8. **Write `PLAN.md`** в каталоге phase'а.

**Outputs:**
- `.planning/roadmap/wave-N-*/phases/NN.M-<slug>/PLAN.md`
- Handoff envelopes готовы к emit

**Handoff:**
- Если `ui-spec:` present → emit `tech.oriion.plan.ui_phase.v1` к `designer` FIRST,
  parallel backend track готов
- Иначе → emit `tech.oriion.plan.task.v1` batch к implementers

---

## Workflow 2 — Re-plan after reviewer revision-request

**Trigger:** CloudEvent `tech.oriion.review.revision.v1` от `reviewer-backend`,
`reviewer-frontend`, или `reviewer-security`. PLAN.md уже существует, Cycle counter < 3.

**Inputs:**
- Existing `PLAN.md`
- `revisions/<phase>-<reviewer>.md` (один или несколько — если parallel reviewers оба
  вернули revisions)
- Original phase-spec (для context)
- Current git diff (через read-only access) для understanding what's been implemented

**Steps:**

1. **Check cycle counter.** Если current cycle = 3 — НЕ re-plan, escalate к `architect`
   через `tech.oriion.conflict.escalation.v1` с `conflict_type: cycle-exhaustion`.
   Architect готовит escalation packet для founder.

2. **Read all revision docs.** Не делай assumptions. Каждая revision имеет file:line
   refs, expected, actual, severity. Группируй по severity (blocker / high / medium).

3. **Check for reviewer conflicts.** Если два reviewer'а requested opposing changes
   (e.g. reviewer-backend «убери rate-limit, performance impact», reviewer-security
   «добавь rate-limit») — escalate к `architect` через
   `tech.oriion.conflict.escalation.v1` с `conflict_type: reviewer-disagreement`. НЕ
   пытайся самостоятельно резолвить — это `architect`'s domain.

4. **Identify changed task scope.** Каждое blocker/high finding → либо modify existing
   task либо add new task. Update Task graph table.

5. **Re-validate dependencies.** Новые tasks могут породить new dependencies — update
   parallel-groups.

6. **Increment Cycle counter.** `Cycle: 2 of 3` → `Cycle: 3 of 3`.

7. **Write re-plan diff section.** В начало PLAN.md добавь:

   ```markdown
   ## Re-plan diff (Cycle N → N+1)
   - Added: T9, T10
   - Changed: T5 (scope expanded to include rate-limit), T7 (test added)
   - Removed: —
   - Reviewers addressed: reviewer-security (3 findings), reviewer-backend (1 finding)
   ```

8. **Self-audit per checklist** (`checklists/re-plan.md`).

**Outputs:**
- Updated `PLAN.md` with new Cycle, re-plan diff, modified task graph

**Handoff:**
- Emit `tech.oriion.plan.task.v1` к implementers только для changed/added tasks (не
  re-run unchanged tasks)

---

## Workflow 3 — Parallel wave-of-phases planning

**Trigger:** founder призывает planner для setup parallel execution нескольких phase'ов
в рамках одного wave (например, Wave 0 Phase 00.4, 00.5, 00.6 не имеют cross-dependencies
→ можно идти parallel).

**Inputs:**
- Multiple phase-spec'и Wave N (выбранные founder'ом для parallel)
- `roadmap/wave-N-*/PHASES.md` с dependency graph между phases
- `STATUS.md` для understanding текущего progress

**Steps:**

1. **Build cross-phase dependency graph.** Из `PHASES.md` + Dependencies секций каждого
   phase-spec — какие phases blocked-by other phases. Phases с no blockers и shared
   blockers — candidates для parallel.

2. **Verify resource non-collision.** Параллельные phases не должны менять одни и те же
   files. Cross-check file-tree diagrams каждой spec. Если collision — sequencing required,
   не parallel.

3. **Estimate cost per phase.** Через `agent-memory:planner` retrieval similar phases
   (Workflow 1 patterns). Если total parallel cost > monthly cap из `cost-budget.yaml` —
   escalate к founder для approve.

4. **Run Workflow 1 (decomposition) per phase.** Каждый phase получает свой PLAN.md.

5. **Build wave-orchestration document** `.planning/roadmap/wave-N-*/WAVE-PLAN.md`:

   ```markdown
   # Wave N — parallel execution plan

   ## Parallel tracks
   - **Track A:** Phase 00.4 (planner: PLAN.md ready)
   - **Track B:** Phase 00.5 (planner: PLAN.md ready)
   - **Track C:** Phase 00.6 (planner: PLAN.md ready)

   ## Shared dependencies
   - Contracts: iam (Track A reads), multitenancy (Track B writes — sequencing!)

   ## Founder approval gates
   - Each track: tier-3+ tasks require explicit approve per ADR-027
   ```

6. **Coordinate handoff timing.** В каждый PLAN.md добавь section «Cross-track sync
   points» если есть.

**Outputs:**
- N × `PLAN.md` (один per phase)
- `WAVE-PLAN.md` orchestration document

**Handoff:** Emit `tech.oriion.plan.task.v1` batches per track. Founder получает summary
notification с links на все PLAN.md.
