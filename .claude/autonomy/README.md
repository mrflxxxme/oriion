# `.claude/autonomy/` — autonomous-runner config + safety rails

Source-of-truth for the autonomous multi-phase runner per [ADR-037](../../.planning/decisions/ADR-037-autonomous-multiphase-runner.md). Under the runner the **strengthened gate-stack is the merge authority, not the founder's eyes** — so these rails must exist and be green *before* autonomy is switched on (Block A precedes the runner).

## Build blocks (ADR-037)

Detailed, living tracker: [`BUILD-PLAN.md`](./BUILD-PLAN.md).

| Block | What | Status |
|---|---|---|
| **A — Rails** | evidence schema + `ci-evidence` + tripwire config + branch protection | ✅ PR #74 |
| **B — Front** | auto-discuss / escalation policy + decisions-log + judge-panel | ✅ PR #75 |
| **C — Runner** | `/autonomy:run` + auto-merge-on-green + RUN-QUEUE + `/autonomy:ack` + premerge hook + role-loader + notify | 🚧 this PR |
| D — Self-healing | auto-revert + fix-loop + post-merge regression-watch | ⬜ todo |
| E — Parallelism | opt-in worktree for independent tracks | ⬜ todo |

Branch protection on `main` is live (require PR + `ci-evidence`/`ci-security`; linear history). The protection toggles are founder-owned switches with ready commands — see `BUILD-PLAN.md`.

## Files here

| File | Role |
|---|---|
| `tripwire.yaml` | **D2 back tripwire.** Path-globs for the 5 categories that must NOT auto-merge (DB migrations · auth/RBAC/sessions · billing · secrets/keys · public contracts). The runner classifies the PR diff against these before auto-merging; a match → RUN-QUEUE + notify + wait for founder `/ack`. |
| `evidence-schema.json` | **D3 gate integrity.** JSON-Schema for a local-only-gate evidence artifact. |
| `escalation-policy.md` | **D4 front escalation.** What the agent owns (all impl+arch, decide+log) vs escalates (product/market + tripwire). Read by `/autonomy:discuss`. |
| `judge-panel.md` | **D5 optimality.** Wide-fork trigger + N-approach generation + `evaluator` rubric + winner/graft + evidence emission. |
| `BUILD-PLAN.md` | Living Block A–E tracker (incl. the founder-owned protection toggles). |
| `settings.hook-snippet.json` | **D2 hook config (founder-armed).** Merge its `hooks` key into `.claude/settings.json` to arm the pre-merge tripwire hook. Claude cannot self-install hook config. |
| `notify.json` *(optional, founder-created)* | `{"telegram_chat_id": "<id>"}` — enables the runner's Telegram phone-ack notifications (D8). Without it: desktop push + RUN-QUEUE only. |

Scripts (`scripts/autonomy/`): `verify_evidence.py` (D3) · `classify_tripwire.py` (D2) · `log_decision.py` (D4) · `run_queue.py` (D8 interrupt queue) · `premerge_hook.py` (D2 hook) · `load_role.py` (role spawn-prompt composer).
Commands: `/autonomy:discuss <phase>` (D4) · `/autonomy:run [queue]` (D6 runner) · `/autonomy:ack [RQ-ID verdict]` (founder resolve).

## Evidence protocol (D3) — how a phase proves a local-only gate

GitHub CI can't run funded live goldens, Docker integration, or the adversarial audit. So a phase that runs them must leave **committed, commit-bound proof**:

1. The gate script writes `evidence/<gate>.json` conforming to `evidence-schema.json`, with `head_sha` = the exact commit it ran against and `verdict` = `PASS`/`FAIL`.
2. The phase declares which gates are required in `evidence/manifest.json`:
   ```json
   { "phase": "01.5", "required_gates": ["live_golden_memory", "adversarial_audit"] }
   ```
3. The `ci-evidence` workflow runs `scripts/autonomy/verify_evidence.py`, asserting every declared gate exists, is **fresh** (`head_sha` == PR head), and `PASS`. Otherwise the merge is blocked.

**Freshness is the teeth:** if the agent commits more code after generating evidence, the branch tip advances and the evidence goes stale → CI fails → the gate must be re-run against the final commit. The agent physically cannot merge green by claiming a gate it didn't run against the merged code. `evidence/` is also the founder's post-hoc audit trail.

`verify_evidence.py` is stdlib-only (runs as bare `python`, no venv) and ASCII-clean (safe on a Windows cp1251 console for local runs). It exits 0 when there's no manifest — phases without local-only gates are unaffected.

### Run the verifier locally

```sh
python scripts/autonomy/verify_evidence.py            # against `git rev-parse HEAD`
python scripts/autonomy/verify_evidence.py --head-sha <sha>
```

## Founder one-time actions (deliberately NOT automatable — these arm the machine)

- ✅ **Branch protection** — done (require PR + `ci-evidence`/`ci-security` required checks; linear history).
- ⬜ **Arm the pre-merge hook:** merge the `hooks` key from [`settings.hook-snippet.json`](./settings.hook-snippet.json) into `.claude/settings.json`.
- ⬜ **Toggles 2/3** (enforce_admins, delete_branch_on_merge) — ready commands in [`BUILD-PLAN.md`](./BUILD-PLAN.md).
- ⬜ **Telegram phone-ack:** get your `chat_id` (message the bot once; или `/telegram:access`), then create `.claude/autonomy/notify.json` with `{"telegram_chat_id": "<id>"}`.
