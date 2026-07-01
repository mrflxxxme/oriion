---
description: Self-healing — detect a red main, auto-revert the offending merge, run the autonomous fix-loop (ADR-037 D7)
argument-hint: [check | revert <sha> | fix <sha>] (default: check → full protocol)
allowed-tools: Read, Grep, Glob, Bash, PowerShell, Edit, Write, Agent, TaskCreate, TaskUpdate, ToolSearch
---

# /autonomy:heal — auto-revert + autonomous fix-loop (ADR-037 D7)

Main must be **green by construction**: a post-merge regression is reverted first, fixed second. Development continues; the fix-loop is autonomous; the founder is ALWAYS notified about a revert. Mode: **$ARGUMENTS** (default = full protocol).

## 1. Detect
`python scripts/autonomy/check_main_health.py` → exit 0 = healthy (done, report); exit 20 = the JSON verdict lists failing workflows + `offender_sha` (the squash-merge commit whose head the failing run tested); exit 1 = cannot judge → RUN-QUEUE `stuck` + notify, STOP (do not merge anything while blind).

Before reverting, sanity-check attribution: `git log origin/main --oneline -5` — confirm `offender_sha` is a recent (runner-era) merge commit; if the failure predates the newest merges or the sha isn't on main, STOP → RUN-QUEUE `stuck` with the verdict JSON + notify (mis-attribution is worse than a pause).

## 2. Revert (main green by construction)
1. `git fetch origin main` → branch `claude/revert-<sha7>` off `origin/main`.
2. `git revert --no-edit <offender_sha>` (squash-merges are plain commits — a direct revert; never `--force` on main; the revert itself is reversible).
3. If the revert conflicts (a later merge built on top): do NOT resolve creatively — RUN-QUEUE `stuck` (details: conflicting paths) + notify, STOP.
4. PR (`revert: <original title>` + link the failing run URL) → wait `gh pr checks --watch` → merge. A revert PR is still gated (ci-evidence/ci-security required; enforce_admins on) — that's intended.
5. **Notify (mandatory, D7):** RUN-QUEUE `revert` entry (offender sha/PR, failing workflows, fix-branch name) + PushNotification + Telegram (`notify.json`). The founder must learn about every revert when it happens.

## 3. Fix-loop (autonomous)
1. Branch `claude/fix-<sha7>` off fresh `origin/main`; `git cherry-pick <offender_sha>` to re-apply the reverted work (resolve mechanical conflicts with the revert commit; if semantic conflicts → `stuck` + notify).
2. Diagnose from the failing run's logs (`gh run view <run_id> --log-failed`) — fix the actual regression, add/adjust the test that SHOULD have caught it (a regression that survived the gates = a gate gap; close it).
3. Full local gates (`make lint typecheck test` + the phase's evidence gates re-run at the new HEAD) → PR → checks green → tripwire classify (`classify_tripwire.py`) → merge on exit 0, or RUN-QUEUE `ack-needed` on exit 10 (the original offender may well be tripwire-класс — that's fine, ack it).
4. Max **3 fix cycles** (mirror ADR-027 §6): still red after 3 → RUN-QUEUE `stuck` with full diagnosis + notify, leave the branch for the founder.
5. On success: resolve the story in RUN-QUEUE (`complete` entry: revert PR + fix PR + root cause one-liner) + `log_decision.py --kind impl --fork "regression root-cause" ...` so the audit trail closes.

## Guardrails
- ONE offender at a time: if multiple workflows fail on different shas, revert the NEWEST first, re-check health, iterate.
- Never revert a founder-authored (non-runner) commit without an explicit ask — `stuck` + notify instead.
- Never force-push, never bypass hooks, never resolve revert conflicts by dropping other phases' work.
