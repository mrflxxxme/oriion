# backend-implementer — memory & persistence

## Owned namespaces

| Namespace | TTL | Что persists |
|---|---|---|
| `agent-memory:backend-implementer` | 180 дней (rotation managed by `memory-curator`) | FastAPI patterns proven, Pydantic-AI structured-output recipes, Alembic migration pitfalls, common task structures by bounded context |
| `phase-state:<phase-id>` | До phase DONE + 30d (per memory-curator policy) | Per-task progress, commit refs, test results, lint status — append-only writes |

## What MUST persist

### After each task commit (`tech.oriion.code.commit.v1` emitted)

```
key: task-<phase-id>-<task-id>-complete
value:
  phase_id: <id>
  task_id: <id>
  commit_sha: <sha>
  bounded_context: <context>
  files_changed: [<paths>]
  contract_refs_used: [<refs>]
  tests_added_count: <int>
  cycle: <int>
  self_audit_passed: <bool>
  duration_seconds: <int>
  tokens_used: <int>
namespace: phase-state:<phase-id>
```

Используется `verifier` для acceptance check mapping и `memory-curator` для capacity
snapshot в gate-frontmatter.

### After successful pattern (post-review, no revision)

```
key: pattern-<bounded-context>-<pattern-type>-<timestamp>
value:
  bounded_context: <context>   # e.g. "iam"
  pattern_type: "fastapi-endpoint" | "pydantic-schema" | "alembic-migration" | "cloudevent-emit" | "rls-policy"
  pattern_summary: <1-2 sentence>
  code_template: <reusable snippet, sanitized>
  contract_refs_pattern: [<ref-formats>]
  passed_review_first_try: <bool>
  reviewer_notes: <any positive feedback patterns>
namespace: agent-memory:backend-implementer
embedding: ONNX 384-dim from pattern_type + bounded_context + summary
```

Используется для retrieval перед similar future task — reuse battle-tested patterns.

### After failed pattern (revision required)

```
key: pitfall-<bounded-context>-<pitfall-type>-<timestamp>
value:
  bounded_context: <context>
  pitfall_type: "rls-missing" | "naming-drift" | "test-gap" | "cross-context-coupling" | "amend-attempted"
  description: <what went wrong>
  reviewer: <role>
  finding_severity: <blocker | high | medium | low>
  resolution: <what fixed it>
  prevention_rule: <pre-commit check to add>
namespace: agent-memory:backend-implementer
embedding: ONNX 384-dim from pitfall_type + description
```

Retrieved перед similar task to avoid repeat mistakes.

## What MUST NOT persist

- **Secrets, credentials, API keys** — никогда. Если accidentally landed в namespace —
  immediate delete request через `tech.oriion.memory.deprecate.v1` к memory-curator.
- **Founder personal data** — никогда.
- **Full code files** — store снippets как pattern templates, не full files. Files в git.
- **Phase-spec content** — domain founder/architect.
- **Other roles' work content** — только refs (commit SHA, file paths).

## Embedding strategy

ONNX `all-MiniLM-L6-v2` (384-dim) per ADR-023 §6. HNSW search через
`memory_search_unified`. Patterns indexed по bounded_context + pattern_type для precise
retrieval.

## Retrieval patterns

### Before Workflow 1 (new endpoint):

```
memory_search_unified(
  query=f"fastapi endpoint {bounded_context} {endpoint_path_segment}",
  namespaces=["agent-memory:backend-implementer"],
  k=5,
  filter={ "pattern_type": "fastapi-endpoint", "bounded_context": <context> }
)
```

Цель: найти analogous endpoint pattern (например, любой `POST /auth/*` имеет similar
structure: Pydantic request → service → response model).

### Before Workflow 2 (migration):

```
memory_search_unified(
  query=f"alembic migration {bounded_context} {table_name}",
  namespaces=["agent-memory:backend-implementer"],
  k=5,
  filter={ "pattern_type": "alembic-migration" }
)
```

Plus query pitfalls:

```
memory_search_unified(
  query=f"alembic pitfall {bounded_context}",
  namespaces=["agent-memory:backend-implementer"],
  k=3,
  filter={ "pattern_type": "alembic-migration-pitfall" }
)
```

Avoid repeat mistakes.

### Before Workflow 3 (CloudEvent):

```
memory_search_unified(
  query=f"cloudevent emit {bounded_context} {event_type}",
  namespaces=["agent-memory:backend-implementer"],
  k=3
)
```

### Before Workflow 4 (fix from revision):

```
memory_search_unified(
  query=f"pitfall {finding_type}",
  namespaces=["agent-memory:backend-implementer"],
  k=10
)
```

Check, не повторяется ли same pitfall pattern.

## Cross-session continuity

При spawn после context overflow:

1. Read `STATUS.md` для active phase
2. Read `PLAN.md` для текущей phase
3. `memory_list(namespace="phase-state:<active-phase>", limit=20, sort="recent")` —
   recent task history
4. `memory_list(namespace="agent-memory:backend-implementer", limit=10, sort="recent")` —
   recent patterns
5. `git log --oneline -n 20 feature/<branch>` — what's been committed

Restore full implementation context.

## Pruning policy

`memory-curator` owns rotation:
- `agent-memory:backend-implementer` entries > 180d → rotation candidate (founder
  approve)
- `phase-state:<phase-id>` → moved к `archive:phase-state:<phase-id>` after phase DONE + 30d

Backend-implementer emit `tech.oriion.memory.deprecate.v1` to memory-curator для явно
устаревших entries (e.g. pre-async patterns после full async migration).

## Audit trail

Каждая mutation своего namespace и каждый commit reflected в memory store entry.
Commit SHAs позволяют через год reconstruct ровно что было сделано на каждом step.
