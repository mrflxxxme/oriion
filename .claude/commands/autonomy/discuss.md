---
description: Auto-discuss a phase — resolve forks autonomously per ADR-037 D4, escalating only product/market + tripwire
argument-hint: <phase-id> (e.g. 01.5)
allowed-tools: Read, Grep, Glob, Bash, Edit, Write
---

# /autonomy:discuss — autonomous phase discussion (ADR-037 D4)

Run the front-autonomy routine for phase **$1**. You are replacing the interactive 7-fork grill with autonomous decide-and-log, escalating only where the founder's judgment is structurally required.

## Contracts to load first (JIT)
- `.claude/autonomy/escalation-policy.md` — what you own vs escalate.
- `.claude/autonomy/judge-panel.md` — how to handle wide forks.
- `.planning/agent-handbook/00-START-HERE.md` — bootstrap-4, dual-tree guard (anchor `.planning/` to the active worktree).

## Steps

1. **Bootstrap.** Read the phase spec for **$1** (`.planning/roadmap/**/phases/$1-*.md`) + `STATUS.md` + `HANDOFF.md`. Ground every claim in the code, not memory (grep, don't assume).
2. **Enumerate forks.** List every real decision the phase needs. For each: the options + your recommended default with a rationale against the optimality rubric.
3. **Classify each fork** per `escalation-policy.md`:
   - **product/market** or **tripwire-category** → **ESCALATE**: draft the escalation record (the format in the policy). Do NOT decide it. Continue independent forks.
   - **agent-owned** → decide it.
4. **Resolve owned forks.**
   - **Wide fork** (architecture/algorithm/schema, high blast radius) → run the judge-panel (`judge-panel.md`): N approaches → `evaluator` rubric → winner + graft.
   - **Narrow** → take the recommended default.
5. **Log every owned decision** with `scripts/autonomy/log_decision.py` (`--kind arch --adr …` for architectural — write the ADR too; `--kind impl` otherwise). Pass `--phase $1`.
6. **Emit the plan.** Produce `PLAN.md` for the phase: the resolved decisions, the task decomposition, `wide_fork:`/`escalated:` flags, and the pipeline template. If any fork escalated, list what is **blocked pending `/ack`** and what can proceed now.

## Output
- A short summary: N forks total → X owned+logged, Y escalated (with the escalation records).
- The `PLAN.md` path.
- If nothing escalated: say so — the phase is ready to execute autonomously.

## Guardrails
- Never invent values for `TBD_*` placeholders (see `PLACEHOLDERS.md`) — those are literals.
- Never decide a product/market or tripwire fork yourself, even if the default seems obvious — escalate it.
- Respect the fixed stack (ADRs). A deviation is itself an architectural decision → ADR + log.
