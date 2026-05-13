# memory-curator — memory & persistence

## Authority

**Memory-curator owns ALL AgentDB namespaces** for management purposes. Other roles write
to their own namespaces, but memory-curator is the single authority for:
- `memory_delete` operations (exclusive)
- Namespace rotation (`phase-state:X` → `archive:phase-state:X`)
- Embedding refresh
- Audit log integrity
- TTL enforcement

Roles write to their own `agent-memory:<role>` через `memory_store` без curator
permission. Cross-namespace writes (e.g. memory-curator writes to `adr-patterns` shared
с architect) — documented in source role's memory.md.

## Namespaces inventory

| Namespace | Owner (write) | TTL | Curator action |
|---|---|---|---|
| `agent-memory:architect` | architect | Permanent | Embedding refresh only |
| `agent-memory:planner` | planner | 180d | Rotation candidates list (founder approves) |
| `agent-memory:memory-curator` | self | 180d | Self-managed |
| `agent-memory:designer` | designer | 180d | Rotation candidates |
| `agent-memory:frontend-implementer` | frontend-implementer | 180d | Rotation candidates |
| `agent-memory:backend-implementer` | backend-implementer | 180d | Rotation candidates |
| `agent-memory:reviewer-frontend` | reviewer-frontend | 90d | Rotation candidates |
| `agent-memory:reviewer-backend` | reviewer-backend | 90d | Rotation candidates |
| `agent-memory:reviewer-security` | reviewer-security | 90d | Rotation candidates |
| `agent-memory:verifier` | verifier | 90d | Rotation candidates |
| `agent-memory:evaluator` | evaluator | Permanent | Embedding refresh only (golden dataset patterns) |
| `phase-state:<phase-id>` | planner (writes), all roles (append handoffs) | До `status: DONE` + 30d | Workflow 2 rotation |
| `archive:phase-state:<phase-id>` | memory-curator (write-once) | Permanent | Read-only |
| `domain-knowledge:<vertical>` | evaluator + vertical-prompt-author | Permanent | Embedding refresh; version tags |
| `adr-patterns` | architect + memory-curator | Permanent | Workflow 3 indexing |

## What MUST persist (own memory)

### After Workflow 1 (gate auto-fill)

```
key: gate-autofill-wave-N-<timestamp>
value:
  gate_file: <path>
  wave_n: <N>
  fields_auto_filled: [metrics_snapshot, deliverables, adr_delta, risks_delta, capacity_snapshot]
  hard_thresholds_met: <bool>
  validation_passed: <bool>
namespace: agent-memory:memory-curator
```

### After Workflow 2 (archive rotation)

```
key: rotation-<phase-id>-<timestamp>
value:
  phase_id: <id>
  entries_moved: <int>
  cross_refs_preserved: <int>
  oq_closed: [<oq-ids>]
namespace: agent-memory:memory-curator
```

### After Workflow 3 (ADR cross-link sync)

```
key: adr-sync-<adr-id>-<timestamp>
value:
  adr_id: <id>
  catalog_row_added: true
  risks_cross_refs_updated: <int>
  superseded_adrs_marked: [<adr-ids>]
  adr_patterns_indexed: true
namespace: agent-memory:memory-curator
```

(Также cross-write в `adr-patterns` per Workflow 3 step 4.)

### After Workflow 4 (audit)

```
key: audit-week-<YYYY-WW>
value:
  baseline_counts: {<namespace>: <count>}
  findings: {critical, high, medium, low}
  auto_applied: {embeddings_refreshed, cross_refs_fixed}
  rotation_candidates: [<keys>]
namespace: agent-memory:memory-curator
```

## What MUST NOT persist (own)

- **Code, configuration secrets** — никогда.
- **Founder personal data, credentials, API keys** — никогда.
- **Full content other roles' work** — только metadata (counts, dates, statuses). Full
  content в их own namespaces.

## Embedding strategy

ONNX `all-MiniLM-L6-v2` (384-dim) per ADR-023 §6. На каждый `memory_store`:
1. Calculate `value_hash = sha256(serialize(value))`
2. Store `value_hash` в entry metadata
3. Generate embedding from key + summary of value (first 200 chars или explicit
   `embed_text` field в value)
4. На subsequent writes — compare `value_hash`; if changed → refresh embedding

## Retrieval patterns

### For Workflow 4 (weekly audit):

```
all_namespaces = memory_bridge_status()
for ns in all_namespaces:
  entries = memory_list(namespace=ns, include_metadata=True)
  for entry in entries:
    check TTL, hash, ownership audit log
```

### Cross-session continuity:

При spawn после context overflow:

1. Read `STATUS.md` для текущего phase состояния
2. Read latest `.planning/_meta/audits/agentdb-*.md` (recent audit)
3. `memory_list(namespace="agent-memory:memory-curator", limit=20, sort="recent")` —
   последние 20 own actions
4. `memory_bridge_status()` — current namespace counts baseline

Restore full operational context.

## Pruning policy (own namespace)

Self-rotation: entries старше 180 дней → `archive:agent-memory:memory-curator`. Не
требует founder approve (это own data, lifecycle owner = self).

## Embedding refresh schedule

Triggered:
1. On `memory_store` if value_hash changed (immediate)
2. Workflow 4 weekly audit (catch missed)
3. Founder explicit `tech.oriion.embedding.refresh.all.v1` (rare, e.g. after model upgrade)

## Strict no-go rules

- **Никогда не модифицируй `archive:*` entries.** Hard error, не silent fail.
- **Никогда не deleteируй ADR files** (даже superseded). Files на диске immutable.
- **Никогда не auto-fix policy violations** (deprecated terms, $-numbers). Escalate.
- **Никогда не fill founder fields в gate-file** (`status: PASSED/BLOCKED`, narrative
  body, `closed_at`). Only 5 specific frontmatter sections.
- **Никогда не делай `memory_delete` без явного trigger** (own rotation OR
  `tech.oriion.memory.deprecate.v1` от owner role OR founder approve).
