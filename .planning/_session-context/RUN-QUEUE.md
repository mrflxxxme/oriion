# RUN-QUEUE — autonomous runner interrupt queue

> Append-only log of runner interrupt events (ADR-037 D8): ack-needed / escalation / revert / stuck / complete. Pending entries are waiting for the founder; resolve with `/autonomy:ack <ID> <verdict>`. Written by `scripts/autonomy/run_queue.py`.

### RQ-20260701-001 | escalation | pr:- | phase:01.5 | 2026-07-01T22:19:35Z | status:pending
- Summary: Co-editing scope: y-websocket real-time sync server in 01.5 or defer
- Fork: does 01.5 ship the real-time co-editing sync layer, or REST-only Yjs persistence? Options: A) full y-websocket sync server now B) REST-only Yjs snapshot/update persistence now, real-time sync deferred until a co-editing UI exists (01.12+/Wave 2). Agent's lean: B - no Wave-1 UI surface can co-edit; storage layer is identical under both; y-websocket adds an infra component with zero consumers now; ADR-012 already fixes Yjs as the document substrate so B precludes nothing. Why escalated: which feature is in-scope for a wave = product/market per escalation-policy D4. Blocks: NOTHING in this PR (B is the substrate for A); ack determines whether a follow-up sync-server phase is queued. Resolve: /autonomy:ack <ID> approved (=B) or revise <ID> <note>.
- Resolve: `/autonomy:ack RQ-20260701-001 approved|rejected`

### RQ-20260701-002 | escalation | pr:- | phase:01.5 | 2026-07-01T22:20:25Z | status:pending
- Summary: Storage quotas per tariff: enforce at upload in 01.5 or track-only
- Fork: ADR-012 defines per-tariff storage limits (Trial 1GB / Solo 5GB / Team 10-200GB). Enforce now or defer? Options: A) enforce caps at upload admission in 01.5 incl. breach UX (reject vs warn) - touches billing surface B) track per-cell byte usage in artifacts context now (cheap aggregate), enforcement + breach UX in a billing follow-up phase. Agent's lean: B - enforcement semantics are a user-visible commercial term (founder domain) and touch the billing tripwire surface; usage tracking is the substrate either way. Why escalated: pricing/tariff commercial term per escalation-policy D4 + billing tripwire adjacency at design step. Blocks: NOTHING in this PR. Resolve: /autonomy:ack <ID> approved (=B) or revise <ID> <note>.
- Resolve: `/autonomy:ack RQ-20260701-002 approved|rejected`
