# Front escalation policy (ADR-037 D4)

The front-side mirror of the back tripwire ([`tripwire.yaml`](./tripwire.yaml)). Under the autonomous runner the discuss/plan step does **not** collect founder answers to every fork. The agent **owns** most forks — it decides, records the decision, and proceeds. It **stops and escalates** only for a narrow, explicit class.

This file is the contract the auto-discuss routine ([`/autonomy:discuss`](../commands/autonomy/discuss.md)) reads.

## What the agent OWNS (decide + log, never ask)

Every **implementation** and **architecture** fork. The agent picks the option that best satisfies the optimality rubric (see [`judge-panel.md`](./judge-panel.md)), records it, and proceeds:

- Data-model / schema shape, table layout, index choice (a *new* table — the *migration* still trips the back tripwire at merge, but the design decision is the agent's).
- Algorithm / library / framework choice within the fixed stack (ADR-001…).
- Module boundaries, seam placement, port/adapter design, naming.
- Test strategy, coverage targets, fixture design.
- Which pipeline template, how to decompose the phase, retry/parallelism.
- Refactors, internal API shape (non-public), error taxonomy.

**Logging is mandatory** (this is what replaces founder oversight):
- **Architectural** decision (constrains future phases / sets a precedent) → write a new **ADR** via the house template + `log_decision.py --kind arch --adr ADR-0NN`.
- **Everything else** → `log_decision.py --kind impl` → appends to [`DECISIONS-LOG.md`](../../.planning/_session-context/DECISIONS-LOG.md).

## What the agent ESCALATES (stop, write to RUN-QUEUE, notify, wait)

Only two classes. If a fork is not one of these, the agent must NOT ask — it decides.

### 1. Product / market-facing behavior

Decisions that need the founder's market/ЦА knowledge, which the agent structurally lacks:

- What the **user sees / experiences** (UX flow, wording shown to users, which feature is in-scope for a wave).
- **Pricing / tariffs / credit economics** (any user-visible commercial term).
- **Scope cuts** that change what the product *does* for a customer (deferring a user-facing capability).
- Positioning / messaging / which vertical/segment to prioritize.

> Litmus: *"Would a competent senior engineer with no market context still be guessing?"* If the right answer depends on customers/market/business strategy, not on code — escalate.

> **Already-decided ≠ product fork (grill 2026-07-03).** User-facing content that an ADR / UI-SPEC has already fixed — a wizard string in [ADR-022](../../.planning/decisions/ADR-022-coordinator-wizard-llm-hybrid.md), a product unit name in [ADR-016](../../.planning/decisions/ADR-016-team-first-ux.md), a palette token in [ADR-031](../../.planning/decisions/ADR-031-design-direction-restyling.md) — is **implemented as-is, not re-escalated**: executing an approved spec is engineering, not a new product decision. What escalates is not everything *visible* but everything *undecided-and-visible* — a net-new user-facing choice covered by no ADR/UI-SPEC. Copy/scenarios the agent must originate (e.g. onboarding demo-scenarios, seeded first-task examples) take the **autonomous-draft → founder review-gate** path (same as vertical prompts, ADR-026), not an up-front escalation.

### 2. Tripwire categories (same list as the back tripwire)

DB migrations on existing tables/RLS · auth/RBAC/sessions · billing/money · secrets/keys/crypto · public API-contract breaks. These escalate at the **design** step too (not only at merge), because the *approach* is as sensitive as the diff.

## Decision procedure (auto-discuss runs this per fork)

1. **Enumerate** the fork's options + the recommended default (with rationale against the rubric).
2. **Classify:** product/market? tripwire-category? → **ESCALATE**. Otherwise → **agent-owned**.
3. **Owned + wide fork** (architecture/algorithm/schema, options materially diverge) → run the [judge-panel](./judge-panel.md); pick the winner. **Owned + narrow** → take the recommended default.
4. **Log** (`arch`→ADR, else `impl`).
5. **Escalated** → append an escalation record to `RUN-QUEUE.md` (Block C), `PushNotification` + Telegram, and **block only that fork** — continue any independent work; pause the dependent path until `/ack`.

## Presentation contract — show your work, then ask (founder directive 2026-07-04)

Every founder-facing interrupt — **both** a D4 escalation **and** a D2 tripwire `ack-needed` — must be presented as a *decision with analysis*, never a bare "please ack". The founder's attention is the scarce resource: when pulled in, they must immediately see **why the machine stopped here specifically**, what the real risk/trade-off is, and what the agent recommends. "PR #N needs ack" fails this — it makes the founder re-derive the analysis the agent already did.

**Required shape of any interrupt (the RUN-QUEUE entry AND the chat/Telegram/push summary):**
1. **What tripped / the fork** — the concrete thing (category + the specific files/behavior), one line.
2. **Analysis** — the *real* risk or judgment, not the generic category blurb: what would go wrong under the worst reasonable interpretation, and what makes it safe (or not) *here*, with evidence (gates, adversarial verdict, what the diff actually does).
3. **Options** — A/B/C with honest trade-offs; always include "hold / request changes", not only "approve".
4. **Recommendation** — the agent's lean **and why**, against the optimality rubric. Take a position.
5. **Ask** — the explicit decision, and how to answer: `/autonomy:ack <id> approved` **or** a direct in-session instruction (an in-session founder decision is an equally authoritative ack — the agent then records it via `run_queue.py resolve <id> --verdict approved` and proceeds).

For a **batch** of related interrupts (e.g. a stacked phase run), present them in **one** message with per-item analysis + a single recommended path (e.g. merge order), so the founder clears the batch in one pass. When the session is interactive, surface the decision through the interactive question tool with options + recommendation inline.

Litmus before sending: *"Have I shown the founder I stumbled on something that genuinely needs their judgment — or am I asking them to rubber-stamp?"* If the latter and the fork was truly agent-ownable, don't escalate (own + log). If it's a real tripwire/product gate, do the analysis **for** them.

## Escalation record format (→ RUN-QUEUE.md)

```
### ESCALATION · <phase> · <UTC ts> · <product-market|tripwire:<category>>
- Fork: <one line — what tripped / the decision>
- Analysis: <real risk/judgment; worst reasonable case; what makes it (un)safe here; evidence — gates/adversarial/what the diff does>
- Options: A) … B) … C) hold / request changes …
- Recommendation: <option> — <why, incl. rubric>
- Blocks: <which downstream tasks wait on this>
- Resolve: `/autonomy:ack <id> approved` (or tell the agent in-session)
```

## Grounding — how the 01.4b grill would classify under this policy

From `HANDOFF` (01.4b, 7 forks). Under D4 the agent would have **owned + logged** 5 and **escalated** 2:

| 01.4b fork | Class | Action |
|---|---|---|
| Q1 archetype `memory_curator`/`analyzer` (no migration) | impl/arch | own → ADR/log |
| Q2 two agents, `deepseek-chat` | impl | own → log |
| Q3 summarizer-impl-only vs producer | **product** (a user-facing capability's scope) | **escalate** |
| Q4 `succeeded`-only, all verticals | impl | own → log |
| Q5 fold-in-cap, never reject | impl/arch (billing-invariant) → **tripwire:billing** | **escalate** |
| Q6 in-process live golden now | impl | own → log |
| Q7 deliverable + user_prompt as filter input | impl | own → log |

So this phase would have needed **2 founder touches instead of 7** — and the 2 are exactly the ones where founder judgment actually mattered (product scope + billing).
