# reviewer-security — handoff templates

CloudEvents 1.0 envelopes. Schema authority:
`.claude/agents/_shared/handoff-schema.json`.

## Inbound

### `tech.oriion.code.commit.v1` (from any implementer)

```json
{
  "specversion": "1.0",
  "type": "tech.oriion.code.commit.v1",
  "source": "agent://backend-implementer",
  "id": "<ulid>",
  "time": "<rfc3339>",
  "subject": "phase/<phase-id>/pr/<pr-number>",
  "datacontenttype": "application/json",
  "data": {
    "phase_id": "00.2",
    "pr_number": 42,
    "branch": "feature/wave-0-phase-00.2-custom-jwt-auth",
    "head_sha": "<sha>",
    "tier": 3,
    "bounded_contexts_touched": ["iam"],
    "dependencies_changed": false,
    "llm_surfaces_touched": false,
    "adr_refs": ["ADR-007", "ADR-014"],
    "cycle": 1
  }
}
```

## Outbound

### `tech.oriion.review.report.v1` — verdict = approve

```json
{
  "specversion": "1.0",
  "type": "tech.oriion.review.report.v1",
  "source": "agent://reviewer-security",
  "subject": "phase/<phase-id>/pr/<pr-number>",
  "data": {
    "phase_id": "00.2",
    "pr_number": 42,
    "head_sha": "<sha>",
    "verdict": "approve",
    "cycle": 1,
    "axes_run": ["owasp", "secrets", "dependencies", "rls", "input-validation", "llm-injection"],
    "scans_executed": ["gitleaks", "pip-audit", "semgrep"],
    "minor_findings": [],
    "next_role": "verifier"
  }
}
```

### `tech.oriion.review.report.v1` — verdict = request_changes

```json
{
  "specversion": "1.0",
  "type": "tech.oriion.review.revision.v1",
  "source": "agent://reviewer-security",
  "subject": "phase/<phase-id>/pr/<pr-number>",
  "data": {
    "phase_id": "00.2",
    "pr_number": 42,
    "head_sha": "<sha>",
    "cycle": 1,
    "revisions_file": "revisions/00.2-reviewer-security.md",
    "block_count": 1,
    "major_count": 2,
    "minor_count": 0,
    "next_role": "planner"
  }
}
```

### `tech.oriion.review.report.v1` — verdict = escalate (cycle cap)

```json
{
  "specversion": "1.0",
  "type": "tech.oriion.review.report.v1",
  "source": "agent://reviewer-security",
  "subject": "phase/<phase-id>/pr/<pr-number>",
  "data": {
    "verdict": "escalate",
    "cycle": 3,
    "reason": "cycle-cap-reached",
    "escalation_partner": "architect",
    "history_ref": "revisions/00.2-reviewer-security.md",
    "next_role": "architect"
  }
}
```

### `tech.oriion.security.critical.v1` — SKIP-CYCLE escalation

Fast-path for CVSS ≥ 7.0 / active exploit / secret leak. Sent
simultaneously to founder, architect, memory-curator. Bypasses standard
revision cycle.

```json
{
  "specversion": "1.0",
  "type": "tech.oriion.security.critical.v1",
  "source": "agent://reviewer-security",
  "subject": "phase/<phase-id>/pr/<pr-number>/critical",
  "data": {
    "phase_id": "00.2",
    "pr_number": 42,
    "head_sha": "<sha>",
    "severity": "critical",
    "category": "secret-leak | cve-high | active-exploit | rls-bypass | prompt-injection",
    "cvss_v3_1": 8.6,
    "cve_ids": ["CVE-2024-XXXXX"],
    "evidence": [
      {"type": "file", "path": "backend/src/iam/jwt.py", "line": 12, "excerpt": "SECRET = 'hs256-...'"},
      {"type": "git-history", "ref": "<sha>", "note": "secret present in commit"}
    ],
    "advisory_urls": ["https://nvd.nist.gov/vuln/detail/CVE-2024-XXXXX"],
    "remediation": "Rotate JWT secret at source; remove literal; load via pydantic_settings; rewrite git history before next push or revoke token.",
    "blocks_merge": true,
    "revisions_file": "revisions/00.2-reviewer-security-critical.md",
    "next_role": "founder"
  }
}
```

## `revisions/<phase-id>-reviewer-security.md` template

```markdown
---
phase_id: <id>
reviewer: reviewer-security
cycle: <n>
head_sha: <sha>
opened_at: <rfc3339>
---

# Security revision — phase <id> — cycle <n>

## Blockers (must fix)
| # | severity | file:line | axis | rule | observed | expected | suggested-fix |
|---|---|---|---|---|---|---|---|
| 1 | block | backend/src/iam/jwt.py:12 | secrets | hard-coded-secret | literal HS256 key in source | load via pydantic_settings | move to env, rotate prior value |

## Major (should fix)
...

## Minor (nice to have)
...

## Scans executed
- gitleaks: <result>
- pip-audit: <result>
- semgrep: <result>
- aidefence_scan: <result>
```
