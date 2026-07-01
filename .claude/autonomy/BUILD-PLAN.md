# Autonomy build plan — living tracker

Implements [ADR-037](../../.planning/decisions/ADR-037-autonomous-multiphase-runner.md) (8 decisions D1–D8). Rails (Block A) precede the runner: the founder's consent to full-autonomy merge (D1) is conditioned on the strengthened gates (D2/D3) existing first. Blocks land as focused PRs.

Legend: ✅ done · 🚧 in progress · ⬜ todo

---

## Block A — Safety rails (D2/D3) ✅ (PR #74, merged)

- ✅ `tripwire.yaml` — D2 back-tripwire path-globs
- ✅ `evidence-schema.json` + `verify_evidence.py` + `ci-evidence.yml` — D3 evidence integrity (7/7 tested, non-breaking)
- ✅ `classify_tripwire.py` — D2 diff classifier
- ✅ ADR-037 + cross-refs (015/023/027)
- ✅ **branch protection on `main`** (applied post-merge): require PR (0 approvals) + required checks = `ci-evidence` + 3 `ci-security` jobs; strict off; linear history on; enforce_admins off.

---

## Block B — Front autonomy (D4/D5) 🚧 (this PR)

- 🚧 `escalation-policy.md` — D4: agent owns all impl+arch forks (decide + log); escalates ONLY product/market + tripwire. Classification procedure + decide-and-log + escalation-record format.
- 🚧 `judge-panel.md` — D5: wide-fork trigger + N approaches + `evaluator` rubric (correctness→security→simplicity→cost→perf) + winner/graft + evidence emission.
- 🚧 `log_decision.py` + `.planning/_session-context/DECISIONS-LOG.md` — uniform decision log for post-hoc audit.
- 🚧 `/autonomy:discuss` slash-command — usable auto-discuss routine (D4).

---

## Block C — Runner (D6/D8) ⬜

- ⬜ `/autonomy:run` slash-command — sequential chain `discuss → plan → execute → gates → auto-merge | tripwire-pause → next`, loop until escalation / ack / stuck-gate / empty-queue.
- ⬜ auto-merge-on-green — runner checks `gh pr checks` all-green (incl. path-filtered `ci-backend` actually ran) + `classify_tripwire.py` exit 0, then merges (Squash/Rebase — linear history).
- ⬜ `RUN-QUEUE.md` — pending acks / escalations / reverts + diagnosis (D8).
- ⬜ notifications — `PushNotification` on 5 interrupt events + Telegram bridge for phone-ack (one-time `chat_id` setup).
- ⬜ scoped pre-merge tripwire **hook** (`settings.json`) — intercepts the runner's merge step (NOT the founder's manual merges) as defense-in-depth over the runner's explicit `classify_tripwire` step.
- ⬜ **role-prompt loader** — CLOSE THE GAP: the 11 `.claude/agents/<role>/` dirs are handbooks, not spawnable subagents. Runner needs a loader (inject `<role>/system-prompt.md` into a `Task` general-purpose spawn) OR native single-file subagent conversion, so the pipeline can actually delegate to planner/implementer/reviewer/verifier/evaluator.

### Branch-protection toggles folded into Block C (per founder, this session)

These 3 were left as founder-owned during Block A because each has a trade-off; they belong to Block C because that is when the runner starts merging with the founder's token and the trade-offs resolve:

- ⬜ **Toggle 1 — enforce `ci-backend` (+`ci-frontend`) as required checks.** Blocked by their `paths:` filter (a required-but-unrun check deadlocks non-matching PRs). Fix = drop the `paths:` filter so they run on every PR, then `gh api -X POST …/required_status_checks/contexts` add `"lint + typecheck + test + security + license"`. **Decision point:** do this (GitHub-level backstop on tests) vs rely on the runner's in-code `gh pr checks` gate (cheaper CI). Recommend: rely on the runner's gate for auto-merge, add the GitHub requirement only if we want the manual-merge path also hard-gated.
- ⬜ **Toggle 2 — `enforce_admins = true`** (`gh api -X POST …/branches/main/protection/enforce_admins`). Makes gates the *true* merge authority — even the runner's admin-token merge must satisfy required checks. Flip WHEN the runner goes live (Block C), so a runaway runner cannot merge red. Trade-off: founder must temporarily disable it for an emergency hotfix past a red gate.
- ⬜ **Toggle 3 — `delete_branch_on_merge = true`** (`gh api -X PATCH repos/mrflxxxme/oriion -f delete_branch_on_merge=true`). Currently `false` despite ADR-027 §3a claiming `true` (design-vs-reality drift). Under the runner (many PRs) auto-teardown keeps the branch list clean. Low-risk; can flip anytime.

---

## Block D — Self-healing (D7) ⬜

- ⬜ post-merge regression-watch — after each auto-merge, on the next phase's CI (or a re-run), attribute a newly-red `main` gate to the offending merge.
- ⬜ auto-revert — `git revert` the offending merge (main green by construction) + notify (D8).
- ⬜ autonomous fix-loop — re-plan → fix → gates → re-merge the reverted work.

---

## Block E — Parallelism (D6) ⬜

- ⬜ opt-in worktree parallelism for genuinely-independent phase tracks (dependency check before parallelizing; sequential is the default).
- ⬜ per-run token budget-cap (`budget.total`) honoring `cost-budget.yaml` (R-31).
