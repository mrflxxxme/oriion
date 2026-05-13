# Checklist — security review

Run top-to-bottom. Any unchecked `must` line → `severity: block` (unless
sev ≥ critical, then fast-path per `workflows.md` playbook 2). Cite
`file:line` and the controlling rule (OWASP A0X / ADR-NN §M / CVE) for
every finding.

## 1. OWASP Top 10 — Broken Access Control (A01) (must)

- [ ] Every state-changing endpoint requires authentication.
- [ ] Every endpoint that returns multi-tenant data enforces cell_id /
      user_id filter (RLS + application-level check both present).
- [ ] No "trust the URL" patterns (path-id used directly without
      ownership check).
- [ ] Role checks (system_roles) executed before action, not after.
- [ ] No IDOR: object access goes through repository methods that filter
      by current actor.

## 2. OWASP Top 10 — Cryptographic Failures (A02) (must)

- [ ] No literal secrets / keys in source (run secret-pattern catalogue
      from memory).
- [ ] Password hashing = argon2id (per ADR-014).
- [ ] JWT secrets loaded via pydantic_settings.
- [ ] TLS not bypassed in fetch / requests (`verify=False` forbidden).
- [ ] PII at rest encrypted per ADR-014 (BYOK keys, OAuth tokens).
- [ ] No use of MD5 / SHA-1 for security purposes.

## 3. OWASP Top 10 — Injection (A03) (must)

- [ ] No SQL string interpolation. Use SQLAlchemy ORM or `text(...)`
      with bound params.
- [ ] No shell exec on user input (`subprocess.run(..., shell=True)`).
- [ ] No `eval` / `exec` on user input.
- [ ] No XSS surface in HTML responses (templates auto-escape; no raw
      `Markup(user_input)`).
- [ ] No SSRF via outbound URL fetches without allowlist.

## 4. OWASP Top 10 — Insecure Design (A04) (should)

- [ ] State-changing endpoints have rate-limiting / idempotency.
- [ ] No "fail open" defaults on critical paths.
- [ ] Workflow boundaries enforce business invariants (not only DB
      constraints).

## 5. OWASP Top 10 — Security Misconfiguration (A05) (must)

- [ ] CORS: no wildcard `*` with `Access-Control-Allow-Credentials: true`.
- [ ] Cookies: `Secure`, `HttpOnly`, `SameSite=Lax|Strict` per role.
- [ ] CSP headers configured for HTML responses (frontend).
- [ ] No debug mode enabled in any non-test path
      (`FastAPI(debug=False)`).
- [ ] No stack traces returned to client in production handlers.
- [ ] Dockerfile: no `latest` tag; pinned base image hash; non-root USER.
- [ ] GitHub workflows: pinned actions by SHA; no `pull_request_target`
      with checkout of untrusted ref.

## 6. OWASP Top 10 — Vulnerable Components (A06) (must)

- [ ] `npm audit --json` shows no advisory ≥ HIGH on changed deps.
- [ ] `pip-audit --strict` shows no vuln ≥ HIGH on changed deps.
- [ ] Lock-file changes match manifest changes (no stealth bump).
- [ ] No deprecated dep flagged as no-longer-maintained.

## 7. OWASP Top 10 — Identification & Auth Failures (A07) (must)

- [ ] Rate-limit on auth endpoints (per-IP + per-account).
- [ ] Refresh-token rotation invalidates prior token atomically.
- [ ] Account-enumeration mitigated (same response shape for "unknown
      user" vs "wrong password").
- [ ] MFA enforcement intact where ADR-014 requires it.

## 8. OWASP Top 10 — Software & Data Integrity (A08) (must)

- [ ] Webhook signatures verified before any state change.
- [ ] Deserialisation: no `pickle.load` on untrusted bytes; YAML uses
      `safe_load`.
- [ ] Supply-chain: GitHub actions pinned by SHA; package mirrors
      verified.

## 9. OWASP Top 10 — Logging & Monitoring Failures (A09) (must)

- [ ] No secret / token / full prompt / PII in logs (per ADR-014 DLP).
- [ ] Auth failures logged (login, refresh, MFA).
- [ ] Role-change events logged.
- [ ] Billing-state changes logged with actor + before/after.

## 10. OWASP Top 10 — SSRF (A10) (must)

- [ ] Outbound HTTP from user input goes via allowlist.
- [ ] Cloud-metadata IP (169.254.169.254) blocked in egress.
- [ ] DNS rebinding mitigated (resolve once, pin IP).

## 11. RU data residency (must — per ADR-001 / ADR-014)

- [ ] No outbound personal-data egress to non-RU endpoint.
- [ ] DB connection strings point to RU-region instances.
- [ ] Object storage URLs are Yandex Cloud (RU region).

## 12. LLM prompt-injection (must — if LLM-facing PR)

Delegate to `checklists/critical-cve-response.md` for sev escalation
path; for non-critical findings:

- [ ] User-controlled text wrapped in delimiter before model call.
- [ ] System prompt instructs model to treat delimited content as
      untrusted data.
- [ ] Tool descriptions escaped before injection into prompt.
- [ ] Model output not rendered as raw HTML / not exec'd as shell.
- [ ] Tool-call from model gated by planner before execution.
- [ ] Probe library run; all probes pass (model refuses; no extraction).

## 13. Secret-history scan (must — every PR)

- [ ] `gitleaks detect` on the PR branch returns no finding.
- [ ] `git log -p -S<each-secret-pattern>` returns no match in branch
      history.
