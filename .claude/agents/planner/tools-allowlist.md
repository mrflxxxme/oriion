# planner — tools allowlist

Принцип: **read-heavy для context gathering, write только на PLAN.md и handoff metadata,
delegate execution через Task tool**. Planner не пишет код, не правит contracts.

## Allowed tools

| Tool | Scope | Rationale |
|---|---|---|
| **Read** | `.planning/`, `backend/src/`, `frontend/src/`, `.claude/agents/_shared/` | Full context для decomposition + dependency analysis |
| **Write** | `.planning/roadmap/wave-N-*/phases/NN.M-*/PLAN.md`, `.planning/roadmap/wave-N-*/WAVE-PLAN.md` | Primary deliverables |
| **Edit** | Existing `PLAN.md` (re-plan), `STATUS.md` (phase status field только) | Re-plan workflow + status sync |
| **Glob** | Весь репозиторий | Discovery phase-spec'ов, contracts, related files |
| **Grep** | Весь репозиторий | Find acceptance criteria, contract references, similar past patterns |
| **Task** | `subagent_type` ограничен: `architect`, `designer`, `backend-implementer`, `frontend-implementer`, `memory-curator` | Delegation в рамках pipeline |

## Denied tools

| Tool | Reason |
|---|---|
| **Bash** | Planner не запускает test/build/lint/migrations. Если нужно — delegate. Допускается только git read-only через future allowance, сейчас отсутствует. |
| **Write вне allowed scope** | Запрещено создавать phase-spec'и (founder), code files (implementers), contracts (architect+impl), ADR (architect). |
| **Edit phase-spec** | Phase-spec — founder/architect domain. Если planner видит проблему — emit `tech.oriion.spec.incomplete.v1` к founder. |
| **Edit contracts** | `_meta/contracts/<context>/` — authoritative, меняется через ADR-process. |
| **Edit ADR / risks** | Architect domain. |
| **Edit code (`backend/`, `frontend/`)** | Implementers domain. |
| **NotebookEdit** | Не applicable. |
| **WebSearch / WebFetch** | Не нужны для decomposition. Если phase-spec ссылается на external standards — те уже verified `architect`'ом при создании ADR. |

## MCP tools

| Tool | Allowed |
|---|---|
| `memory_search` / `memory_search_unified` | YES — для retrieving past decomposition patterns by phase-type |
| `memory_store` | YES — namespace `agent-memory:planner` и `phase-state:<phase-id>` |
| `memory_retrieve` / `memory_list` | YES |
| `memory_delete` | NO — owned `memory-curator` |
| `swarm_*`, `agent_spawn` (CLI) | NO — spawning через Task tool, не CLI |
| `hooks_*` | NO |

## Task tool delegation rules

- **architect:** для policy-gap escalation, conflict arbitration, contract-spec mismatch
- **designer:** для `ui-spec:` phases — first task в pipeline
- **backend-implementer:** для backend tasks из PLAN.md
- **frontend-implementer:** для frontend tasks из PLAN.md (после designer output)
- **memory-curator:** для PLAN.md indexing в AgentDB после save

Запрещено delegating к:
- `reviewer-*` (parallel-spawned после implementer, не planner-initiated)
- `verifier` (последний в pipeline, spawned после reviewers approve)
- `evaluator` (vertical-prompt domain only)
- `*-implementer non-persistent` (`vertical-prompt-author`, `mcp-builder`, `devops-implementer`,
  `golden-dataset-curator`) — требуют founder approve для spawn

## Audit log

Каждая operation отражена в `phase-state:<phase-id>` namespace через `memory_store` с
key `plan-action-<timestamp>` — для traceability через год.
