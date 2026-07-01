# `.claude/autonomy/` — autonomous-runner config + safety rails

Source-of-truth for the autonomous multi-phase runner per [ADR-037](../../.planning/decisions/ADR-037-autonomous-multiphase-runner.md). Under the runner the **strengthened gate-stack is the merge authority, not the founder's eyes** — so these rails must exist and be green *before* autonomy is switched on (Block A precedes the runner).

## Build blocks (ADR-037)

| Block | What | Status |
|---|---|---|
| **A — Rails** | evidence schema + `ci-evidence` + tripwire config + pre-merge hook + branch protection | 🚧 in progress (this dir) |
| B — Front | auto-discuss / escalation policy + decisions-log + judge-panel | ⬜ todo |
| C — Runner | `/autonomy:run` + auto-merge-on-green + RUN-QUEUE + notify + Telegram bridge | ⬜ todo |
| D — Self-healing | auto-revert + fix-loop + post-merge regression-watch | ⬜ todo |
| E — Parallelism | opt-in worktree for independent tracks | ⬜ todo |

## Files here

| File | Role |
|---|---|
| `tripwire.yaml` | **D2 back tripwire.** Path-globs for the 5 categories that must NOT auto-merge (DB migrations · auth/RBAC/sessions · billing · secrets/keys · public contracts). The runner classifies the PR diff against these before auto-merging; a match → RUN-QUEUE + notify + wait for founder `/ack`. |
| `evidence-schema.json` | **D3 gate integrity.** JSON-Schema for a local-only-gate evidence artifact. |

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

## Founder one-time actions (not automatable from here)

- **Branch protection:** add `ci-evidence` (alongside `ci-backend`, `ci-security`, `ci-frontend`) to the required status checks on `main`, so a stale/missing evidence artifact actually blocks the merge button. Requires repo-admin — do via GitHub settings or `gh api`.
- **Telegram bridge (Block C):** one-time channel setup to save a `chat_id` for phone-side `/ack` (`/telegram:configure`).
