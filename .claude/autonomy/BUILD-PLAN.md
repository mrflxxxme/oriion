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

## Block C — Runner (D6/D8) ✅ (PR #76, merged)

- ✅ `/autonomy:run` slash-command — sequential chain `discuss → plan → execute → gates → auto-merge | tripwire-pause → next`, loop until escalation / ack / stuck-gate / empty-queue. Post-merge regression = Block-D stub (stop + notify, no auto-revert yet).
- ✅ auto-merge-on-green — explicit runner step: `gh pr checks` all-green + `classify_tripwire.py` exit 0 → squash-merge (linear history); exit 10 → RUN-QUEUE `ack-needed` + notify.
- ✅ `RUN-QUEUE.md` machinery — `scripts/autonomy/run_queue.py` (add/resolve/check-ack/pending; tested 8-step lifecycle) + `/autonomy:ack` founder command (1-click approve → completes the merge; rejected/escalation verdicts feed the decisions-log).
- ✅ notifications — runner instructions: PushNotification on the 5 interrupt events + optional Telegram phone-ack via `.claude/autonomy/notify.json` (`{"telegram_chat_id": "..."}`; founder one-time setup, see README).
- ✅ pre-merge tripwire **hook** — `scripts/autonomy/premerge_hook.py` (tested 6/6 against real PRs: clean-allow / tripwire-block with categories / ack-unblock / fail-closed on unparseable-merge input / BOM-tolerant). **FOUNDER ACTION to arm:** merge `settings.hook-snippet.json` into `.claude/settings.json` — Claude is (correctly) not permitted to self-install hook config.
- ✅ **role-prompt loader** — `scripts/autonomy/load_role.py` composes a spawnable prompt from `.claude/agents/<role>/` (system-prompt + tools-allowlist + optional workflows/checklist; tested against all 11 roles). The runner passes it to general-purpose `Task` spawns for bespoke variants.
- ✅ **native role subagents (ADR-040 D8, 01.8c)** — the 11 roles are now spawnable `.claude/agents/<role>.md` entries (`subagent_type=<role>`, isolated context), superseding the "gap closed without converting" note above: judge-panel + reviewer lenses spawn real roles directly; `load_role.py` stays for one-off composed prompts. Conformance gated by `scripts/autonomy/check_subagents.py` (`ci-autonomy`).

### Branch-protection toggles (flipped 2026-07-02 on explicit founder ask)

- ✅ **Toggle 2 — `enforce_admins = true`** — verified via read-back; even the runner's admin-token merge must satisfy required checks. Rollback: `gh api -X DELETE repos/mrflxxxme/oriion/branches/main/protection/enforce_admins`.
- ✅ **Toggle 3 — `delete_branch_on_merge = true`** — verified; aligns reality with ADR-027 §3a.
- ⬜ **Toggle 1 — enforce `ci-backend` as required check.** DECIDED: rely on the runner's in-code `gh pr checks` all-green gate. Revisit if the manual-merge path needs a GitHub-level backstop (requires dropping the `paths:` filter first — a required-but-unrun check deadlocks non-matching PRs).

### Armed the same day (explicit founder ask)
- ✅ `.claude/settings.json` — pre-merge tripwire hook live (PreToolUse on Bash|PowerShell → `premerge_hook.py`).
- ✅ `.claude/autonomy/notify.json` — telegram phone-ack channel (founder chat_id).

---

## Block D — Self-healing (D7) 🚧 (this PR)

- ✅ regression-watch — `scripts/autonomy/check_main_health.py`: latest completed run per gate-workflow on main → verdict JSON + `offender_sha` attribution (exit 0/20/1; deploy-staging excluded; in-progress runs ignored; **tested 4/4**: live-healthy + red-fixture-attribution + empty + in-progress-ignored).
- ✅ auto-revert + notify — `/autonomy:heal` §2: revert branch off fresh main → gated revert-PR → merge → **mandatory RUN-QUEUE `revert` + push + Telegram** (founder always learns of a revert). Attribution sanity-check + conflict/foreign-commit guards → `stuck`, never guess.
- ✅ autonomous fix-loop — `/autonomy:heal` §3: cherry-pick the reverted work → diagnose from `gh run view --log-failed` → fix + close the gate gap (add the missing test) → full gates + tripwire → merge/ack; max 3 cycles → `stuck`.
- ✅ run.md step 9 stub replaced: health-check BEFORE each next merge + at run end; exit 20 → heal protocol; exit 1 → no merges while blind.

---

## Block E — Parallelism (D6) 🚧 (this PR)

- ✅ opt-in worktree parallelism — run.md §Parallel tracks: only for provably-independent phases (no shared bounded contexts / no PHASES.md dependency edge / not tripwire-heavy); executor subagents with `isolation: "worktree"` + background, max 2 tracks; **merges always serialized** through the health-check (one offender at a time for D7 attribution).
- ✅ per-run budget accounting — run.md §Budget: estimate at run end into the `complete` entry; panels + fix-loops count toward dev_team caps; degrade panel N when tight (R-31).

---

## Post-build (after the 01.5 pilot)

- ⬜ pilot retro: what the runner escalated/paused/healed on 01.5 → tighten tripwire globs / escalation-policy wording where it misfired.
- ⬜ consider Toggle 1 (GitHub-level ci-backend requirement) if manual merges become common.
