# reviewer-backend — workflows

Three playbooks. Pick the one matching the inbound handoff envelope.

## 1. PR review walkthrough (inbound: `tech.oriion.code.commit.v1`)

**Trigger.** Backend-implementer emits commit-handoff for a backend PR.

**Steps.**
1. **Load context.**
   - Read `profile.md` axes ranking (already loaded).
   - Read `phase-state:<phase-id>` from AgentDB → get PLAN.md goals,
     acceptance criteria, ADR-refs.
   - Read every `_meta/contracts/<context>/*.yaml|*.sql` touched by the diff.
   - Read recurring-anti-patterns block from `agent-memory:reviewer-backend`.
2. **Enumerate diff surface.**
   - `git diff --name-only main...HEAD` (read-only Bash).
   - Classify each file into: contract, source, migration, test, config,
     docs.
3. **Run checklist** `checklists/pr-review-backend.md` axis-by-axis.
   - For each finding: capture `severity / file:line / axis / observed /
     expected / suggested-fix`.
4. **If diff includes Alembic migration** → branch into
   `checklists/migration-safety.md`. Block PR if any "must" line fails.
5. **Decide verdict.**
   - 0 `block` findings → `approve` (still list `minor` for awareness).
   - ≥1 `block` finding → `request_changes`.
   - Architectural drift not solvable in this PR → `escalate` with
     `architect` partner.
6. **Emit handoff** per `handoff-templates.md`.
7. **Persist learning** to memory (see `memory.md`): new anti-pattern
   variant, confirmed false-positive, per-context invariant.

**Exit.** Handoff envelope emitted; cycle count updated in memory.

## 2. Migration safety audit (inbound: same envelope, migration present)

**Trigger.** Step 4 above OR explicit `pipeline-role: migration-audit` field.

**Steps.**
1. Read every file under `backend/alembic/versions/` in the diff.
2. For each revision file, check `checklists/migration-safety.md`:
   - upgrade() AND downgrade() both implemented.
   - downgrade() actually inverse-restorable (no data-destroying default).
   - Index creation `op.create_index(..., postgresql_concurrently=True)`
     for hot tables.
   - RLS policy migrated in same revision as the table.
   - No exclusive lock on tables listed in
     `agent-memory:reviewer-backend / hot-tables`.
3. Read schema.sql for affected bounded-context, confirm migration converges
   the actual DB to the contract.
4. Verify alembic head linearises: `alembic history` must show single head.
5. Findings flow into the verdict from playbook 1 (do not emit a separate
   handoff — migrations are part of the PR).

## 3. Re-review after revision (inbound: `tech.oriion.code.commit.v1`, cycle>1)

**Trigger.** Implementer pushed a fix-up commit referencing the prior
`revisions/<phase>-reviewer-backend.md`.

**Steps.**
1. Read previous `revisions/<phase>-reviewer-backend.md`.
2. For each finding in that file:
   - Find the corresponding fix in the new commits via
     `git log --oneline main..HEAD -- <file>`.
   - Re-check the specific `file:line`. Mark `resolved` / `partial` /
     `regressed`.
3. **Also re-check the surrounding 20 lines** of each fix to catch
   collateral regressions.
4. Cycle count bookkeeping:
   - If `cycle == 3` and any `block` remains → `verdict: escalate` with
     `escalation_partner: architect`, payload includes full revision
     history.
   - Else if all `block` resolved → `verdict: approve`.
   - Else → new `revisions/...` (incremented cycle).
5. Emit handoff.

**Hard stop.** Never start cycle 4. Cycle 3 with unresolved blocks = escalate.
