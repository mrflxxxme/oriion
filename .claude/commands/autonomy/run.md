---
description: Autonomous multi-phase runner — discuss→plan→execute→gates→PR→auto-merge, chained until escalation/ack/stuck/queue-empty (ADR-037 D6)
argument-hint: [phase-ids... | next N | until <phase>] (default: next 1)
allowed-tools: Read, Grep, Glob, Bash, PowerShell, Edit, Write, Agent, Skill, TaskCreate, TaskUpdate, ToolSearch
---

# /autonomy:run — autonomous multi-phase runner (ADR-037 D6/D7-stub/D8)

You are the runner. The strengthened gate-stack is the merge authority — NOT the founder's eyes. You chain phases in THIS session (no per-phase re-bootstrap) until an interrupt or the queue is empty. Queue: **$ARGUMENTS** (default: the next phase per `.planning/STATUS.md` / `PHASES.md`).

## Contracts (load JIT, in this order)
1. `.planning/agent-handbook/00-START-HERE.md` — bootstrap-4 + dual-tree guard.
2. `.claude/autonomy/escalation-policy.md` (D4) + `judge-panel.md` (D5) + `tripwire.yaml` (D2).
3. `.claude/agents/_shared/cost-budget.yaml` — dev_team caps; honor per-day soft/hard.

## Preflight (once per run)
- `git rev-parse --show-toplevel` — anchor; sync `origin/main`; work off fresh `main`.
- Docker: check `docker info`. **NEVER start Docker yourself** (founder-controlled). If down → integration/live gates are unavailable: phases whose manifest needs them go to RUN-QUEUE as `stuck`, pick the next phase that doesn't.
- Funded `.env`: run `python scripts/autonomy/provision_env.py` — it copies the canonical funded `backend/.env` (kept git-ignored on the **main checkout**) into the active worktree if absent (idempotent; secret-safe: refuses if the dest isn't git-ignored; never prints values). Exit 0 = present/provisioned; exit 2 = no canonical env configured → live goldens unavailable, same stuck-path as Docker-down (proceed with phases that don't need them). NEVER commit `.env` (tripwire `secrets_keys_crypto` + gitleaks).
- Note the per-run budget: dev_team per_day soft $30 / hard $75. Track approximate spend; STOP the run at hard cap (add `stuck` entry: budget).

## Per-phase loop
For each phase P in the queue:

1. **Branch** `claude/auto-<P>-<slug>` off fresh `origin/main`.
2. **Discuss** — run the `/autonomy:discuss` routine for P (own+log via `log_decision.py`; wide forks → judge-panel; product/tripwire forks → escalate). If a fork escalates: RUN-QUEUE `escalation` + notify (see Interrupts); if it blocks the whole phase → skip P (leave branch), continue with the next INDEPENDENT phase; else proceed on the unblocked part.
3. **Plan** — PLAN.md per planner role; pin tasks via TaskCreate.
4. **Execute** — atomic commits (ADR-027 format, `Pipeline-role:` field). Delegate to roles via Agent tool: compose prompts with `python scripts/autonomy/load_role.py --role <role> [--checklist <c>]` + task context. Reviews: relevant reviewer roles (parallel where independent). Stagnation kill-switch: no commit/file-write/status-update for 30 min wall-clock → abort task, RUN-QUEUE `stuck` + notify (ADR-015 §5).
5. **Gates** — local CI-equivalent: `make lint typecheck test` (+ integration if Docker up) + per-module gates as the phase demands. Local-only gates (live goldens / docker-integration / adversarial audit / judge-panel) MUST write `evidence/<gate>.json` (schema `.claude/autonomy/evidence-schema.json`, `head_sha` = final commit) + declare in `evidence/manifest.json`. **Re-run evidence gates if you commit after generating them** (freshness is enforced by ci-evidence).
6. **Exit ritual** — JOURNAL append + HANDOFF rewrite (house rule; review-gate blocks merge without it).
7. **PR** — `gh pr create` (body: what/AC/verification/decisions-log refs). Watch `gh pr checks <N> --watch`; ALL checks green required — including path-filtered `ci-backend`/`ci-frontend` when they triggered (they are not branch-protection-required; YOU are the gate here). Red gate → fix and re-push, max 3 cycles → RUN-QUEUE `stuck` + notify, move on.
8. **Tripwire classify (explicit step)** — `uv run --project backend python scripts/autonomy/classify_tripwire.py --diff-base origin/main` (exit 0 = clean; 10 = matched). The premerge hook re-checks this at the merge command — defense-in-depth.
   - **exit 0** → `gh pr merge <N> --squash --delete-branch` (linear history). 
   - **exit 10** → RUN-QUEUE `ack-needed` (`run_queue.py add --kind ack-needed --pr <N> --phase <P> --summary ... --details "Categories: ..."`) + notify. Do NOT merge. Continue with the next phase ONLY if independent of P; else stop the loop (leave everything green + documented).
9. **Post-merge regression watch (D7)** — don't block on every merge waiting for main's CI (~3 min): run `python scripts/autonomy/check_main_health.py` (a) BEFORE each next merge and (b) at run end. Exit 20 → run the **`/autonomy:heal` protocol** (auto-revert offender → notify → autonomous fix-loop, max 3 cycles); resume the queue after heal merges the fix, stop if heal goes `stuck`. Exit 1 (cannot judge) → no further merges, `stuck` + notify.
10. **Phase complete** — RUN-QUEUE `complete` entry (one line: PR, cost, decisions count). Next phase.

## Interrupts → notify (D8), every time
On the 5 events — **ack-needed / escalation / revert / stuck / run-complete**:
1. `run_queue.py add ...` (the queue IS the founder's single pane of glass).
2. `ToolSearch "select:PushNotification"` → PushNotification (short title + what's waiting).
3. If `.claude/autonomy/notify.json` exists and has `telegram_chat_id` → send the same via the telegram plugin's reply tool to that chat_id (phone-ack path). Absent/fails → desktop push + queue is enough; never block on notification failure.

An `/autonomy:ack <ID> approved` (founder, from any session) unblocks the corresponding merge — the premerge hook honors `run_queue.py check-ack`.

## Parallel tracks (Block E — opt-in, D6)
Sequential is the DEFAULT. Parallelize ONLY when phases are **provably independent**: no shared bounded contexts (compare the phase-specs' touched `src/<context>` + migration dirs), no dependency edge in `PHASES.md`, and neither phase is tripwire-heavy. Then:
- Spawn per-phase executor subagents via the Agent tool with `isolation: "worktree"` + `run_in_background: true` (max **2** concurrent tracks), each producing its own branch + PR through the full per-phase loop (steps 2–7).
- **Merges stay SEQUENTIAL** through steps 8–9 in the main session (one merge → health-check → next merge). Never merge two tracks back-to-back without a health-check between — regression attribution (D7) needs one offender at a time.
- On any doubt about independence — don't parallelize. Wall-clock saved is not worth a cross-track conflict.

## Budget accounting (R-31)
At run end estimate spend (phases × avg task cost vs `cost-budget.yaml` dev_team caps) and include it in the run's `complete` RUN-QUEUE entry. Judge-panels and heal fix-loops count toward the same per-day budget; degrade panel N=3→2 when tight (see judge-panel.md).

## Stop conditions (end the run cleanly)
Queue empty · escalation/ack blocks all remaining phases · budget hard-cap · heal went `stuck` (unfixable regression) · founder says stop. On stop: RUN-QUEUE `complete` summary for the RUN (phases merged / pending acks / escalations / reverts+fixes / spend estimate) + notify.

## Hard rules
- NEVER merge without: all CI checks green + evidence fresh + tripwire exit 0 (or approved ack) + main healthy (check_main_health exit 0).
- NEVER bypass hooks (`--no-verify`), never `--force` (only `--force-with-lease` on feature branches).
- NEVER invent `TBD_*` values; never start Docker; never touch `user_production` config.
- Parallel tracks: max 2, provable independence only, merges always serialized.
