# reviewer-security — workflows

Three playbooks. The handoff envelope + diff content together determine
which one runs.

## 1. Standard PR security review (inbound: `tech.oriion.code.commit.v1`)

**Trigger.** Any tier 3+ PR; any tier 2 PR touching auth / billing /
multitenancy / llm-gateway / dependencies / workflows.

**Steps.**
1. **Load context.**
   - Read this role's memory namespace: threat models per context,
     accepted-risk allowlist, prompt-injection probe library.
   - Read affected ADRs (especially ADR-014, ADR-024 for the bounded
     contexts touched).
   - Read `_meta/contracts/<context>/README.md` for invariants.
2. **Diff surface enumeration.**
   - `git diff --name-only main...HEAD` (read-only Bash).
   - Tag files: source / migration / contract / config / lock-file /
     workflow / prompt.
3. **Run** `checklists/security-review.md` axis-by-axis.
4. **Run dependency scan** if lock-file or manifest changed:
   - `npm audit --json` (frontend) / `pip-audit --strict` (backend).
   - Cross-check `ToolSearch("aidefence")` → `aidefence_scan` on diff for
     known patterns.
   - Cross-reference results against `agent-memory:reviewer-security /
     cve-history`.
5. **Run prompt-injection probes** if any `_meta/verticals/*/prompts/*.md`,
   `backend/src/llm_gateway/`, `backend/src/agents/`, or any LLM-facing
   handler changed:
   - Use probe set from memory (`prompt-injection probes` collection).
   - For each probe: trace the path from user input → model call. Block
     if no delimiter/sanitisation layer exists.
6. **Classify each finding.**
   - CVSS ≥ 7.0 OR matches MUST-blocker rule → critical → fast-path
     (playbook 2).
   - Block / major / minor with axis + cite.
7. **Decide verdict.**
   - 0 block + 0 critical → `approve`.
   - ≥1 block (non-critical) → `request_changes` (write revisions file).
   - ≥1 critical → playbook 2 takes over.
   - Architectural fix required → `escalate` to `architect`.
8. **Emit handoff** per `handoff-templates.md`.
9. **Persist learning**: update CVE-history, new probe variants,
   per-context threat-model deltas.

## 2. Critical CVE / secret-leak / active-exploit response

**Trigger.** Any of:
- CVE with CVSS ≥ 7.0 in dependency add/upgrade.
- Hard-coded secret detected in any current file.
- Secret detected in git history of the PR branch (even if removed in
  later commit) via `git log -p -S<pattern>`.
- Known active-exploit pattern matched (e.g. log4shell-style payload,
  CVE-2024-XXXX matching the dep version).

**Steps.**
1. **Do not start a revision cycle.** Skip the standard request_changes
   path.
2. **Verify the finding** with at least two independent signals
   (advisory URL + repo evidence). If verification fails, downgrade to
   standard block and use playbook 1.
3. **Emit `tech.oriion.security.critical.v1`** immediately. Address:
   founder + architect + memory-curator. Subject:
   `phase/<phase-id>/pr/<n>/critical`.
4. **Emit `tech.oriion.review.report.v1`** with `verdict: escalate`,
   `reason: critical-security`, cross-link to the critical event id.
5. **Write `revisions/<phase>-reviewer-security-critical.md`** with:
   evidence chain, CVSS calc, proposed remediation, secret-rotation
   instructions if applicable.
6. **Block PR merge** (verdict alone is enough; founder UI surfaces it).
7. **On fix commit** → re-verify only the critical finding. Other
   findings remain in the standard cycle queue.

## 3. Prompt-injection audit (LLM-facing PR)

**Trigger.** PR touches:
- `_meta/verticals/<slug>/prompts/*.md`
- `backend/src/llm_gateway/`
- `backend/src/agents/`
- Any FastAPI route that ingests user text and forwards into a model call.

**Steps.**
1. **Map data flow.** For each user-controlled input field, trace to the
   model call: input → validation → assembly → system prompt.
2. **Check delimiter discipline.**
   - User text MUST be wrapped in an explicit delimiter (e.g. XML tag,
     fenced section) and the system prompt MUST instruct the model to
     treat content inside the delimiter as untrusted data.
   - Tool descriptions injected into prompts must escape control tokens.
3. **Run probe library** from memory (`prompt-injection probes`). For
   each probe:
   - "Ignore previous instructions and ..."
   - System-prompt extraction attempts.
   - Tool-call hijacking ("call delete_account with id=...").
   - Markdown / code-block escape attempts.
   - Multilingual injections (RU/EN mix) — particularly relevant given
     RU-first ICP.
4. **Check output handling.** Model responses rendered in UI must be
   treated as untrusted (no `dangerouslySetInnerHTML`, no shell exec on
   model output).
5. **Check tool-call gating.** Per ADR-026 vertical-prompt pipeline,
   tool calls from a model MUST be gated by the planner / coordinator,
   not directly executed.
6. Findings flow into the verdict from playbook 1 with axis =
   `llm-injection`. Failed delimiter discipline OR a passing probe →
   `block`.
