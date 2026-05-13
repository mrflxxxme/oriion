# reviewer-backend — memory

## Namespace

`agent-memory:reviewer-backend` (AgentDB, ONNX 384-dim embeddings, HNSW
index per ADR-023 §6-7).

## What persists across sessions

### 1. Recurring anti-pattern library

Keyed by `(bounded-context, axis)`. Each entry:

```yaml
- key: iam/contract
  pattern: "endpoint returns 500 on expired access-token"
  expected: "api.yaml /auth/* declares 401 token_expired"
  first_seen: <phase-id>
  hits: <int>
  last_seen: <phase-id>
```

When `hits >= 3`, also append a `block` row in the per-context invariant
list below and notify `architect` to consider an ADR amendment.

### 2. Accepted-risk allowlist (false-positives)

Findings that look like blockers but are intentional. Founder-signed-off.

```yaml
- key: billing/test-coverage
  pattern: "no unit test for credit_balance recompute"
  reason: "covered by snapshot integration test in tests/billing/test_ledger.py"
  approved_by: founder
  approved_at: <date>
  approval_ref: PR#<n>
```

The reviewer must **not** auto-add to this list. Only founder-signed PRs
write here.

### 3. Per-context invariants

Hard rules per bounded-context, distilled from contracts + ADR. Reviewer
fails any PR that contradicts these.

```yaml
- context: iam
  invariants:
    - "every table with user_id MUST have RLS policy on (user_id = current_setting('app.user_id')::uuid)"
    - "refresh-token rotation MUST invalidate prior token in same transaction"
    - "JWT secret MUST be loaded from pydantic_settings, never literal"
- context: billing
  invariants:
    - "credit_transactions append-only; never UPDATE/DELETE"
    - "money columns NUMERIC(18,2), never FLOAT"
- context: multitenancy
  invariants:
    - "every domain table has cell_id NOT NULL + RLS policy"
```

### 4. Cycle history (per PR)

```yaml
- pr_number: 42
  phase_id: 00.2
  cycles:
    - {n: 1, verdict: request_changes, block_count: 2}
    - {n: 2, verdict: request_changes, block_count: 1}
    - {n: 3, verdict: approve, block_count: 0}
```

Used at cycle start to enforce the 3-cycle cap from ADR-027 §6.

## What does NOT persist

- Full file contents (re-read from disk every cycle).
- Source of truth contracts (those live in `_meta/contracts/`).
- ADR text (re-read from `.planning/decisions/`).
- Anything containing secrets or tokens.

## Write triggers

- After every verdict emit → upsert anti-pattern + cycle-history entries.
- After founder explicit `accepted-risk` annotation in PR comment → append
  to allowlist (only via signed founder commit, never agent self-write).

## Read triggers

- At pipeline start: load whole namespace into working context.
- Before each verdict: re-query anti-pattern matches by embedding-similarity
  on the current finding text.

## Eviction

None. Append-only with monthly compaction performed by `memory-curator`
(merges duplicate anti-pattern variants by cosine ≥ 0.92).
