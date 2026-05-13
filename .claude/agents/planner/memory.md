# planner — memory & persistence

## Owned namespaces

| Namespace | TTL | Что persists |
|---|---|---|
| `agent-memory:planner` | 180 дней (rotate by `memory-curator`) | Decomposition patterns by phase-type, re-plan cycle metrics, common task structures |
| `phase-state:<phase-id>` | До `status: DONE` + 30 дней | Current phase plan history, handoff trail, cycle counter, reviewer history |

## What MUST persist

### After Workflow 1 (decomposition)

```
key: decomposition-pattern-<phase-type>-<timestamp>
value:
  phase_type: "backend-endpoint" | "frontend-page" | "migration-only" | "vertical-prompt" | "full-stack"
  pipeline_template: "backend-feature" | "frontend-feature" | "full-stack-feature"
  task_count: <int>
  parallel_groups: <int>
  estimated_tiers:
    tier_1: <count>
    tier_2: <count>
    tier_3: <count>
    tier_4: <count>
  decomposition_heuristics_applied: [<heuristic-ids>]
namespace: agent-memory:planner
embedding: ONNX 384-dim from phase title + first task descriptions
```

Используется при future decomposition similar phase-type для consistency и speed.

### After Workflow 2 (re-plan)

```
key: re-plan-<phase-id>-cycle-<N>
value:
  phase_id: <id>
  cycle: <N>
  reviewer: <reviewer-role>
  findings_count: { blocker, high, medium, low }
  tasks_changed: { added, modified, removed }
  resolution_time_seconds: <int>
namespace: phase-state:<phase-id>
```

Сводно через 10+ phases — detect patterns: какие reviewers чаще всего бросают revisions,
какие task categories чаще всего fail review → feed planner для future decomposition
(добавлять защитные tasks заранее).

### After Workflow 3 (wave-of-phases)

```
key: wave-orchestration-<wave-N>-<timestamp>
value:
  wave: <N>
  parallel_tracks: <count>
  phases_in_wave: [<phase-ids>]
  cross_phase_dependencies: [<edges>]
  resource_collisions_detected: <count>
  total_estimated_cost_tokens: <int>
namespace: agent-memory:planner
```

## What MUST NOT persist

- **Code snippets** — никогда. Code живёт в git, не в planner memory.
- **Reviewer findings full text** — только counts. Full findings в `revisions/*.md` файлах.
- **Founder personal data, credentials** — никогда.
- **ADR content** — domain `architect` + `adr-patterns` namespace.
- **Vertical-prompt content** — domain `evaluator` + `domain-knowledge:<vertical>`.

## Embedding strategy

ONNX `all-MiniLM-L6-v2` (384-dim) per ADR-023 §6. HNSW search через
`memory_search_unified`. Decomposition patterns embedded по phase title + first 3 task
descriptions — semantic match для analogous phases.

## Retrieval patterns

### Before Workflow 1 (decomposition):

```
memory_search_unified(
  query=phase_title + " " + pipeline_template,
  namespaces=["agent-memory:planner"],
  k=5,
  filter={ "phase_type": <matching-type> }
)
```

Цель: найти прошлые decomposition того же phase-type, reuse task structure (например,
любая «add endpoint» phase даёт 3-5 known tasks: migration → schema → router → tests →
event emit).

### Before Workflow 2 (re-plan):

```
memory_search_unified(
  query="re-plan " + phase_id + " " + reviewer,
  namespaces=["phase-state:" + phase_id, "agent-memory:planner"],
  k=10
)
```

Цель: вспомнить, что менялось в прошлых cycle'ах этой phase + check, не повторяется ли тот
же finding pattern (если да — implementer не пофиксил, escalate раньше cycle 3).

### Before Workflow 3 (wave-of-phases):

```
memory_search_unified(
  query="wave " + N + " orchestration",
  namespaces=["agent-memory:planner"],
  k=3
)
```

Цель: learn from past waves — какие cross-phase collisions встречались, какие parallel
tracks работали vs какие attended sequencing.

## Cross-session continuity

При spawn после context overflow:

1. Read `STATUS.md` для текущего active phase.
2. Read latest `PLAN.md` для текущего phase.
3. `memory_list(namespace="phase-state:<active-phase>", limit=20, sort="recent")` —
   handoff trail + cycle state.
4. `memory_list(namespace="agent-memory:planner", limit=10, sort="recent")` —
   recent decomposition patterns.

Restore full context без потери знаний.

## Phase-state cleanup

После `status: DONE` в gate-file и +30 дней — `memory-curator` rotates
`phase-state:<phase-id>` в `archive:phase-state:<phase-id>` (read-only). Planner НЕ делает
этот rotate сам.

## Pruning policy

`memory-curator` владеет rotation. Planner emit
`tech.oriion.memory.deprecate.v1` к `memory-curator` если pattern явно устарел (например,
old pipeline-template superseded by new).
