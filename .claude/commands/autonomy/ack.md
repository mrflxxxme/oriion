---
description: Resolve a RUN-QUEUE entry — founder's 1-click ack for tripwire merges and escalations (ADR-037 D2/D8)
argument-hint: [RQ-ID approved|rejected [note]] (no args: list pending)
allowed-tools: Read, Bash, PowerShell
---

# /autonomy:ack — founder ack/resolve for the runner's interrupt queue

Arguments: **$ARGUMENTS**

## No arguments → show what's waiting
Run `python scripts/autonomy/run_queue.py pending` and show the founder each pending entry **with its full block** from `.planning/_session-context/RUN-QUEUE.md` (summary, categories, resolve-hint). For `ack-needed` entries also show the PR link and a compact risk digest: `gh pr view <N> --json title,additions,deletions,files` — list ONLY the tripwire-matched files (the founder's 1-click is about those, not the whole diff).

## `<RQ-ID> approved|rejected [note...]`
1. `python scripts/autonomy/run_queue.py resolve <RQ-ID> --verdict <verdict> --note "<note>"`.
2. If the entry is `ack-needed` with `pr:<N>` and verdict **approved**:
   - The premerge hook now allows the merge (`check-ack` passes). Complete it: `gh pr merge <N> --squash --delete-branch`, confirm merged, report.
3. If **rejected**: do NOT merge. Summarize what the runner should change (from the note), and suggest the follow-up (`/autonomy:run` re-entry or a manual session on that branch).
4. For `escalation` entries: the verdict + note IS the founder's product decision — record it via `python scripts/autonomy/log_decision.py --phase <P> --kind escalated --fork "<fork>" --decision "<what founder chose>" --rationale "founder verdict: <note>"` so the decision trail stays complete.

## Guardrails
- Only resolve entries the founder explicitly names. Never bulk-approve.
- If the RQ-ID is unknown/already resolved, say so (exit 4 from the script) — do not guess.
