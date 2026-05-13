# memory-curator — handoff templates

CloudEvents 1.0 envelopes (ADR-024 §3). Common envelope:

```yaml
specversion: "1.0"
type: <event-type>
source: claude-agent://memory-curator
id: <uuid-v4>
time: <ISO-8601>
datacontenttype: application/json
subject: <phase-id-or-wave-id-or-namespace>
data: <payload>
```

---

## Inbound events

### `tech.oriion.phase.complete.v1`

**From:** `verifier`
**Trigger:** verifier marked phase `status: DONE`. Triggers gate auto-fill (если последняя
phase Wave) и/или archive rotation scheduling.

**Payload schema:**

```yaml
data:
  phase_id: "00.2"
  wave: 0
  pr_merged_sha: "abc1234"
  merged_at: "2026-06-15T14:30:00Z"
  is_last_phase_in_wave: false  # если true — trigger Workflow 1
  acceptance_results:
    total: 12
    passed: 12
    failed: 0
  founder_approved: true
```

**Memory-curator response:**
- Always: update STATUS.md row, embed phase final state в `archive:phase-state:` queue
  (фактический rotation через 30 дней)
- If `is_last_phase_in_wave: true` → run Workflow 1 (gate auto-fill)
- Schedule Workflow 2 (archive rotation) для +30 дней через scheduled-tasks

---

### `tech.oriion.adr.merged.v1`

**From:** `architect` (после founder approve через interactive UX)
**Trigger:** new ADR is approved and ready for catalog indexing.

**Payload schema:**

```yaml
data:
  adr_id: "ADR-028"
  adr_file: ".planning/decisions/ADR-028-vertical-prompt-semver.md"
  status: "Accepted"
  supersedes: ["ADR-010"]  # null или array
  informs: ["ADR-026"]
  cross_link_diffs:
    - file: ".planning/decisions/README.md"
      action: "append-row"
      content: "| ADR-028 | Vertical-prompt SemVer | Accepted | ... |"
    - file: ".planning/risks/REGISTER.md"
      action: "update-cross-ref"
      risk_id: "R-31"
      new_ref: "ADR-028 mitigation"
    - file: ".planning/decisions/ADR-010-role-versioning.md"
      action: "update-frontmatter-status"
      new_status: "Superseded by ADR-028"
```

**Memory-curator response:** run Workflow 3 (ADR cross-link sync).

---

### `tech.oriion.memory.deprecate.v1`

**From:** any persistent role
**Trigger:** owner role determines specific entry obsolete, requests delete.

**Payload schema:**

```yaml
data:
  requesting_role: "architect"
  namespace: "adr-patterns"
  key: "adr-005-pattern"
  reason: "ADR-005 superseded by ADR-027, pattern no longer representative"
  preserve_in_archive: true  # default true — move к archive вместо hard delete
```

**Memory-curator response:** verify requesting role owns namespace (or namespace shared
ownership documented). Move к `archive:<namespace>` если `preserve_in_archive: true`,
else hard delete with audit log.

---

### `tech.oriion.gate.refresh.v1`

**From:** founder
**Trigger:** founder hits «refresh gate metrics» action explicitly (e.g. mid-wave check).

**Payload schema:**

```yaml
data:
  wave: 0
  gate_file: ".planning/gates/wave-0-to-1.md"
  founder_notes: "checking interim progress"
```

**Memory-curator response:** run Workflow 1 без emit к founder (founder уже expecting,
return result directly).

---

## Outbound events

### `tech.oriion.gate.metrics_ready.v1`

**To:** `architect`
**Trigger:** Workflow 1 completed, gate-frontmatter 80% filled, ready for invariant audit.

**Payload schema:**

```yaml
data:
  gate_file: ".planning/gates/wave-0-to-1.md"
  wave_n: 0
  wave_n_plus_1: 1
  phases_in_wave: ["00.1", "00.2", "00.3", "00.4", "00.5", "00.6", "00.7"]
  metrics_snapshot_ready: true
  founder_narrative_pending: true
  hard_thresholds_actuals:
    internal_demo:
      required: true
      actual: true
```

---

### `tech.oriion.gate.ready_for_narrative.v1`

**To:** founder
**Trigger:** Same time as above. Founder action required — write narrative + set status.

**Payload schema:**

```yaml
data:
  gate_file: ".planning/gates/wave-0-to-1.md"
  founder_action_required: "fill-narrative-body-and-set-status"
  narrative_sections_pending:
    - "## Decision (founder-narrative)"
    - "## Retro themes"
    - "## Strategic implications"
    - "## Scope changes for Wave 2"
  hard_thresholds_met: true | false
  blocking_thresholds: []  # list если есть unmet
```

---

### `tech.oriion.archive.rotated.v1`

**To:** founder
**Trigger:** Workflow 2 completed, phase rotated to archive.

**Payload schema:**

```yaml
data:
  phase_id: "00.1"
  archive_namespace: "archive:phase-state:00.1"
  archived_at: "2026-07-15T10:00:00Z"
  entry_count_archived: 47
  status_md_updated: true
  rotation_summary_file: ".planning/_meta/audits/archive-00.1-2026-07-15.md"
  oq_closed: ["OQ-13"]  # если phase закрыл open question
```

---

### `tech.oriion.adr.indexed.v1`

**To:** `architect`
**Trigger:** Workflow 3 completed.

**Payload schema:**

```yaml
data:
  adr_id: "ADR-028"
  catalog_updated: true
  risks_register_updated: true
  superseded_adrs_updated: ["ADR-010"]
  adr_patterns_namespace_entry: "adr-028-pattern"
  embedding_refreshed: true
```

---

### `tech.oriion.namespace.audit.v1`

**To:** founder
**Trigger:** Workflow 4 completed.

**Payload schema:**

```yaml
data:
  audit_id: "agentdb-2026-W24"
  audit_file: ".planning/_meta/audits/agentdb-2026-W24.md"
  findings_total: 5
  findings_critical: 0
  findings_high: 1
  findings_medium: 3
  findings_low: 1
  auto_applied:
    embeddings_refreshed: 12
    cross_refs_fixed: 2
  founder_decisions_required:
    rotation_candidates: 3  # founder approves per phase
    namespace_consolidation: false
```

---

### `tech.oriion.conflict.escalation.v1`

**To:** `architect`
**Trigger:** memory-curator detected policy violation (deprecated terms, double
authoritativity, $-numbers в restricted files, ownership leak).

**Payload schema:**

```yaml
data:
  conflict_type: "hygiene-violation" | "namespace-ownership-leak" | "double-authoritativity"
  detail:
    file_or_namespace: <path-or-namespace>
    violation_type: "deprecated-term" | "inline-ddl" | "economic-numbers" | ...
    line_refs: [<file:line>]
  memory_curator_action_taken: "flagged-no-fix"
  rationale: "auto-fix would be policy override — escalating"
```

---

### `tech.oriion.phase.stuck.v1`

**To:** founder
**Trigger:** phase progress stuck (cycle counter not incrementing, no new commits, no
reviewer activity) > 3 дней.

**Payload schema:**

```yaml
data:
  phase_id: "00.2"
  last_activity_at: "2026-06-10T08:00:00Z"
  days_stuck: 4
  current_cycle: 2
  current_pipeline_step: "reviewer-security"
  suspected_blocker: "reviewer waiting on architect arbitration"
  recommendation: "founder ping reviewer-security or trigger escalation"
```

---

## Envelope validation

Каждый outbound event валидируется против `.claude/agents/_shared/handoff-schema.json`
перед emit. Invalid → error log + abort + escalate к founder.
