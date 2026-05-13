# architect — handoff templates

Все handoffs — CloudEvents 1.0 envelopes (per ADR-024 §3). Common envelope:

```yaml
specversion: "1.0"
type: <event-type>
source: claude-agent://architect
id: <uuid-v4>
time: <ISO-8601>
datacontenttype: application/json
subject: <phase-id-or-adr-id>
data: <event-specific-payload>
```

---

## Inbound events

### `tech.oriion.grill.decision.v1`

**From:** founder
**Trigger:** founder завершил grill-сессию и хочет, чтобы architect задрафтил соответствующие ADR.

**Payload schema:**

```yaml
data:
  session_id: "session-2026-05-13-002"
  session_detail_ref: ".planning/_meta/GRILL-DECISIONS-ORIION.md#session-2"
  decisions:
    - id: "DECISION-12"
      title: "Vertical-prompt SemVer auto-bump on golden-dataset regression"
      summary: "..."
  founder_notes: "Want ADR draft within 24h; happy to iterate"
```

**Architect response:** запустить Workflow 1 (ADR drafting).

---

### `tech.oriion.conflict.escalation.v1`

**From:** `reviewer-backend`, `reviewer-security`, или `verifier` после исчерпания 3 циклов.
**Trigger:** conflicting verdicts ИЛИ 3 цикла reviewer ↔ implementer исчерпаны.

**Payload schema:**

```yaml
data:
  phase_id: "00.2"
  pr_ref: "feature/wave-0-phase-00.2-custom-jwt-auth"
  pr_sha: "abc1234"
  conflict_type: "reviewer-disagreement" | "cycle-exhaustion" | "policy-gap"
  parties:
    - role: "reviewer-backend"
      verdict: "approve"
      revision_doc: ".planning/.../revisions/00.2-reviewer-backend.md"
    - role: "reviewer-security"
      verdict: "revision-request"
      revision_doc: ".planning/.../revisions/00.2-reviewer-security.md"
  cycle_count: 3
  affected_adrs: ["ADR-007", "ADR-014"]
  affected_contracts: ["_meta/contracts/iam/"]
  diff_summary: "JWT refresh rotation endpoint + RLS policy"
```

**Architect response:** запустить Workflow 3 (arbitration). Decide self-arbitrate vs escalate.

---

### `tech.oriion.gate.metrics_ready.v1`

**From:** `memory-curator`
**Trigger:** wave-gate frontmatter заполнен на 80%, нужен cross-phase invariant audit перед founder-narrative phase.

**Payload schema:**

```yaml
data:
  gate_file: ".planning/gates/wave-0-to-1.md"
  wave_n: 0
  wave_n_plus_1: 1
  phases_in_wave: ["00.1", "00.2", "00.3", "00.4", "00.5", "00.6", "00.7"]
  metrics_snapshot_ready: true
  founder_narrative_pending: true
```

**Architect response:** запустить Workflow 2 (cross-phase invariant audit).

---

## Outbound events

### `tech.oriion.adr.draft.v1`

**To:** founder (через interactive Claude Code UX per ADR-023 §8b)
**Trigger:** Workflow 1 завершён, ADR draft готов к review.

**Payload schema:**

```yaml
data:
  adr_id: "ADR-028"
  adr_file: ".planning/decisions/ADR-028-vertical-prompt-semver.md"
  source_decision: "DECISION-12"
  source_session: "session-2026-05-13-002"
  status: "Proposed"
  supersedes: []
  informs: ["ADR-010", "ADR-026"]
  cross_link_diffs:
    - file: ".planning/decisions/README.md"
      action: "append-row"
    - file: ".planning/risks/REGISTER.md"
      action: "update-cross-ref"
      risk_id: "R-31"
  founder_action_required: "review-and-approve-or-revise"
  self_audit_checklist: ".claude/agents/architect/checklists/adr-creation.md"
  self_audit_passed: true
```

---

### `tech.oriion.audit.report.v1`

**To:** `memory-curator`
**Trigger:** Workflow 2 завершён.

**Payload schema:**

```yaml
data:
  audit_id: "audit-2026-06-15-wave-0-gate"
  audit_file: ".planning/_meta/audits/audit-2026-06-15-wave-0-gate.md"
  scope: "wave-0-pre-gate"
  findings_total: 4
  findings_critical: 1
  findings_high: 1
  findings_medium: 2
  findings_low: 0
  has_p_audit_2_blockers: true  # требует cleanup в той же PR
  founder_attention_required: true
  gate_file_ref: ".planning/gates/wave-0-to-1.md"
```

Если `has_p_audit_2_blockers: true` — параллельно emit `tech.oriion.conflict.escalation.v1`
к founder.

---

### `tech.oriion.arbitration.decision.v1`

**To:** `reviewer-backend`, `reviewer-security`, и связанный `*-implementer` (parallel
delivery).
**Trigger:** Workflow 3 self-arbitration done ИЛИ founder вернул решение через escalation.

**Payload schema:**

```yaml
data:
  phase_id: "00.2"
  arbitration_id: "arb-2026-06-15-001"
  decision_doc: ".planning/.../revisions/00.2-architect-arbitration.md"
  decision_summary: "Apply rate-limit (10 req/min/IP) on /auth/refresh; rationale: security inviolable per ADR-014"
  source: "architect-self-arbitrated" | "founder-decided-via-escalation"
  binding: true
  cycle_count_at_arbitration: 3
  follow_up_actions:
    - role: "backend-implementer"
      action: "implement rate-limit middleware per spec section X"
    - role: "reviewer-security"
      action: "verify implementation matches arbitration decision"
```

После arbitration — cycle counter resets (max 3 цикла action). Если новый conflict — снова
escalation.

---

## Envelope validation

Каждый outbound event валидируется против `.claude/agents/_shared/handoff-schema.json`
перед emit. Если payload не conform — error log + abort emit + escalate к founder.
