# architect — memory & persistence

## Owned namespaces

| Namespace | TTL | Что persists |
|---|---|---|
| `agent-memory:architect` | Permanent | Cross-phase invariant catalog, arbitration decisions, audit findings patterns, recurring policy gaps |
| `adr-patterns` (shared read/write с `memory-curator`) | Permanent | Pattern-search для архитектурных решений: ADR-template variations, common cross-link structures, supersedes-chain history |

## What MUST persist (write на каждой relevant операции)

### After Workflow 1 (ADR drafting)

```
key: adr-pattern-<adr-id>
value:
  source_decision: <grill-decision-id>
  template_variant: "standard" | "supersedes" | "informs-multiple"
  cross_link_targets: [decisions/README, risks/REGISTER, superseded-adrs]
  consequences_categories: [reuse, cost, naming, gate, ...]
namespace: adr-patterns
embedding: ONNX 384-dim from ADR title + first §Decision paragraph
```

### After Workflow 2 (audit)

```
key: audit-pattern-<audit-id>
value:
  audit_scope: "wave-N-gate" | "ad-hoc" | "post-pr"
  findings_by_category:
    deprecated_terms: <count>
    naming_drift: <count>
    bounded_context_coupling: <count>
    economic_numbers_leak: <count>
    adr_cross_ref_gaps: <count>
  resolution_pattern: "in-same-pr" | "deferred-to-milestone-C" | "escalated"
namespace: agent-memory:architect
```

Recurring finding pattern (one category > threshold across multiple audits) → trigger
proposal для process improvement (например, pre-commit hook для deprecated-term scan).

### After Workflow 3 (arbitration)

```
key: arbitration-<arbitration-id>
value:
  phase_id: <phase-id>
  conflict_type: <type>
  parties: [reviewer-backend, reviewer-security]
  resolution: "self-arbitrated" | "escalated"
  invariant_invoked: [bounded-context | naming | founder-approve | economic-numbers | ...]
  trade_off_statement: <one-sentence>
  cycle_count_at_arbitration: <int>
namespace: agent-memory:architect
```

Используется для (a) consistency check на повторных similar конфликтах (decision должен
быть consistent с прошлым), (b) detecting policy gaps если escalations происходят часто
по одному и тому же типу.

## What MUST NOT persist

- **Founder personal data, credentials, API keys** — никогда.
- **PR diff content** — сохраняем только refs (sha, file paths), не сам код. Code живёт
  в git.
- **Vertical-prompt content** — это domain `evaluator` и `domain-knowledge:<vertical>`
  namespace.
- **Phase progress / handoff messages** — это `phase-state:<phase-id>` namespace, owned
  `memory-curator`.

## Embedding strategy

Все persisted entries embedded через ONNX `all-MiniLM-L6-v2` (384-dim) per ADR-023 §6.
Используется HNSW vector search для retrieval через `memory_search_unified`. При
context-overflow роль resumes из namespace + STATUS.md.

## Retrieval patterns

### Before Workflow 1 (ADR drafting):

```
memory_search_unified(
  query=<grill-decision-title> + " ADR pattern",
  namespaces=["adr-patterns", "agent-memory:architect"],
  k=5
)
```

Цель: найти analogous ADR (например, новый ADR об API rate-limit может reuse pattern
от ADR-014 security).

### Before Workflow 2 (audit):

```
memory_search_unified(
  query="audit pattern wave-" + N + " findings",
  namespaces=["agent-memory:architect"],
  k=3
)
```

Цель: вспомнить, какие категории findings были common в прошлых audit-pass'ах (например,
если в Wave 0 audit нашли 3 случая naming drift, на Wave 1 audit заранее усилить grep).

### Before Workflow 3 (arbitration):

```
memory_search_unified(
  query=conflict_type + " " + parties.join(" "),
  namespaces=["agent-memory:architect", "adr-patterns"],
  k=10
)
```

Цель: проверить consistency с прошлыми arbitration decisions (similar conflict — similar
resolution, иначе policy drift).

## Cross-session continuity

При spawning после context overflow:

1. Read `STATUS.md` для текущей wave + phase context.
2. Read `decisions/README.md` для catalog state.
3. `memory_list(namespace="agent-memory:architect", limit=20, sort="recent")` —
   последние 20 audits/arbitrations.
4. `memory_list(namespace="adr-patterns", limit=10, sort="recent")` — последние 10 ADR
   patterns.

Этого достаточно для full context restore без потери знаний.

## Pruning policy

`memory-curator` отвечает за rotation. Architect не делает `memory_delete`. При
обнаружении устаревшего pattern (например, ADR superseded) — emit
`tech.oriion.memory.deprecate.v1` к `memory-curator` с целевым key для rotation в
archive namespace.
