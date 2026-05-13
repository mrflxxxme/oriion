# memory-curator — workflows

Четыре canonical playbook'а.

---

## Workflow 1 — Gate frontmatter auto-fill

**Trigger:** один из:
- `tech.oriion.phase.complete.v1` от `verifier` для последней phase в Wave N
- Periodic check каждые 7 дней (scheduled)
- Founder explicit trigger через `tech.oriion.gate.refresh.v1`

**Inputs:**
- `.planning/gates/wave-N-to-N+1.md` (или create from `.planning/gates/_template.md`)
- `.planning/gates/_schema/gate.schema.json` (validation)
- `STATUS.md` (active phases)
- All `phase-state:<phase-id>` namespaces для phases Wave N
- `decisions/README.md` (current catalog)
- `risks/REGISTER.md` (current state)
- Snapshot `decisions/README.md` Wave N start (via git log)
- Snapshot `risks/REGISTER.md` Wave N start (via git log)

**Steps:**

1. **Open / create gate-file.** Если файл не существует — copy from template, заполни
   `gate: wave-N-to-N+1`, `opened_at: <today>`, `status: PENDING`.

2. **Auto-fill `metrics_snapshot`.** Query AgentDB:
   ```
   for phase in phases_in_wave_N:
     entries = memory_list(namespace=f"phase-state:{phase}", filter={key: "telemetry-*"})
     aggregate counts: registrations, TTFV minutes (avg), pass_rate, NPS
   ```
   Заполни поля per ADR-025 frontmatter example.

3. **Auto-fill `deliverables`.** Для каждой phase Wave N:
   ```yaml
   - id: phase-NN.M
     name: <name из spec>
     status: DONE | PARTIAL | BLOCKED   # из STATUS.md
     notes: <last note из PLAN.md "Status changes" секции, если есть>
   ```

4. **Auto-fill `adr_delta`.** Git diff `decisions/README.md` (`HEAD~<wave_start>..HEAD`)
   → extract added ADR IDs + revised ADR IDs (where Status field changed).

5. **Auto-fill `risks_delta`.** Git diff `risks/REGISTER.md`:
   - `closed`: rows where status changed to `closed`
   - `added`: new rows
   - `severity_changed`: rows where severity field changed (e.g. `medium → high`)

6. **Auto-fill `capacity_snapshot`.** Query telemetry (no $-numbers per P-AUDIT-1):
   ```yaml
   founder_hours_logged: <int>
   ai_token_spend_total: <int>  # tokens, не $$
   ```

7. **Fill `hard_thresholds.actual` per ADR-025 §2.**
   - Wave 0→1: `internal_demo.passed.actual` = `true` если verifier confirmed, else `null`
   - Wave 1→2: `friend_feedback.nps.actual`, `acceptance_criteria_pass_rate.actual`
   - и т.д.

8. **Validate frontmatter против schema.** Run `gate.schema.json` validation. Если invalid
   — log error, escalate к `architect`.

9. **Save partial gate-file.** Не trogaем Markdown body — это founder-narrative.
   `status: PENDING` сохраняется.

10. **Self-audit per checklist** (`checklists/gate-autofill.md`).

**Outputs:**
- `.planning/gates/wave-N-to-N+1.md` — partial fill, ready_for_narrative

**Handoff:**
- Parallel: `tech.oriion.gate.metrics_ready.v1` к `architect` (для invariant audit)
- Parallel: `tech.oriion.gate.ready_for_narrative.v1` к founder

---

## Workflow 2 — Phase archive rotation

**Trigger:** `tech.oriion.phase.complete.v1` от `verifier` с `status: DONE`. Wait 30 дней
после complete (через scheduled-tasks или delayed re-trigger).

**Inputs:**
- `phase-state:<phase-id>` namespace
- `STATUS.md`
- Phase каталог (`.planning/roadmap/wave-N-*/phases/NN.M-<slug>/`)
- `PROJECT.md`, `_meta/open-questions.md` (для possible OQ updates)

**Steps:**

1. **Pre-rotation cross-ref scan.** Grep `<phase-id>` по active files:
   - Other `PLAN.md`
   - `roadmap/wave-*-*/PHASES.md`
   - Active ADRs (`decisions/ADR-*.md`)
   - `_meta/*` files
   Если найден active link БЕЗ deprecation marker — preserve link, не abort (cross-refs
   к archived phase OK, файл остаётся).

2. **Move namespace entries.** Для всех keys в `phase-state:<phase-id>`:
   - Read value + metadata
   - Write в `archive:phase-state:<phase-id>` (with `archived_at: <today>`, `archived_by:
     memory-curator`)
   - Delete original entry
   - Preserve ONNX embeddings (re-index в archive HNSW)

3. **Update STATUS.md row.** Phase status: `DONE` → `ARCHIVED`. Add archive date column.

4. **OQ check.** Если phase закрывал OQ-NN (per `_meta/open-questions.md`):
   - Verify OQ status = `closed` в open-questions.md
   - Update `PROJECT.md` если OQ был в active blockers

5. **Compile rotation summary.** `.planning/_meta/audits/archive-<phase-id>-<date>.md`
   short report.

**Outputs:**
- Updated `STATUS.md`
- `archive:phase-state:<phase-id>` namespace populated
- `phase-state:<phase-id>` namespace empty
- Rotation summary file

**Handoff:** `tech.oriion.archive.rotated.v1` к founder (notification, не action-required).

---

## Workflow 3 — ADR cross-link sync to risks/REGISTER

**Trigger:** `tech.oriion.adr.merged.v1` от `architect` (founder уже approved через
interactive UX).

**Inputs:**
- New ADR file `.planning/decisions/ADR-NNN-<slug>.md`
- `decisions/README.md` (current catalog)
- `risks/REGISTER.md` (current state)
- Architect-prepared diffs (из CloudEvent payload `cross_link_diffs`)

**Steps:**

1. **Apply diff `decisions/README.md`.** Append row per architect's diff (catalog format
   preserved — category, ADR-NNN link, status, summary).

2. **Apply diff `risks/REGISTER.md`.** Per architect's diff:
   - `update-cross-ref` action: update affected risks' "Mitigation owners / ADR-refs"
     column to include new ADR
   - `risk-status-change`: e.g. R-31 mitigation now has ADR-028 → status может оставаться
     `open` но severity_changed (architect decides)

3. **If ADR supersedes:** apply architect's diff к старому ADR:
   - Frontmatter `Status: Accepted` → `Status: Superseded by ADR-NNN`
   - Links section update
   - Body НЕ trogaем (immutable record)

4. **Embed new ADR в `adr-patterns` namespace:**
   ```
   memory_store(
     key=f"adr-{adr_id}-pattern",
     value={ source_decision, template_variant, cross_link_targets, consequences_categories },
     namespace="adr-patterns",
     embedding=ONNX(title + first §Decision paragraph)
   )
   ```

5. **Update `agent-memory:architect`** через cross-write (с architect's permission):
   увеличить counter `adr_count` в architect's history.

6. **Validate cross-link integrity.** Grep new ADR ID по affected files — должны быть
   linked. Missing — flag + escalate к `architect`.

**Outputs:**
- Updated `decisions/README.md`
- Updated `risks/REGISTER.md`
- Updated old ADR frontmatter (if supersedes)
- New entry в `adr-patterns` namespace

**Handoff:** `tech.oriion.adr.indexed.v1` к `architect` (confirmation).

---

## Workflow 4 — AgentDB namespace audit

**Trigger:** Weekly scheduled OR founder explicit trigger.

**Inputs:**
- All AgentDB namespaces (list через `memory_bridge_status`)
- TTL policies из memory.md (per role)

**Steps:**

1. **List namespaces + entry counts.** Compile baseline table.

2. **Orphan detection (`phase-state:*`).** Для каждого `phase-state:<phase-id>`:
   - Cross-check `<phase-id>` с STATUS.md active phases
   - Если phase status = `DONE` AND complete_at > 30 дней AND not yet archived → candidate
     для Workflow 2 rotation
   - Если phase отсутствует в STATUS.md вообще → finding (orphan), escalate

3. **Stale detection (`agent-memory:<role>`).** Для каждого entry:
   - Read `last_updated` metadata
   - Если > TTL (default 180 дней) AND `archive_eligible: true` → candidate для rotation
   - Specific role TTL: `agent-memory:architect` = permanent (ADR-patterns immutable);
     `agent-memory:planner` = 180d; `agent-memory:backend-implementer` = 180d; etc

4. **Embedding-freshness detection.** Hash check:
   ```
   for entry in namespace:
     stored_hash = entry.metadata.value_hash
     current_hash = sha256(entry.value)
     if stored_hash != current_hash:
       finding: stale-embedding
       action: refresh ONNX embedding + update value_hash
   ```

5. **Ownership-leak detection.** Audit log per namespace — кто writeал/deleteал. Если
   `memory_delete` пришёл не от memory-curator (audit log) → critical finding, escalate.

6. **Compile audit report.** `.planning/_meta/audits/agentdb-<YYYY-WW>.md`:
   ```markdown
   # AgentDB namespace audit — Week NN

   ## Baseline
   | Namespace | Entry count | Avg size | Embedding freshness |

   ## Findings
   | Severity | Type | Details | Resolution proposal |

   ## Auto-applied actions
   - Refreshed N embeddings
   - Identified M candidates для rotation (founder decides)
   ```

**Outputs:**
- Audit report file
- Refreshed embeddings (auto-applied)
- Rotation candidate list (NOT auto-rotated — founder decides per phase)

**Handoff:** `tech.oriion.namespace.audit.v1` к founder.
