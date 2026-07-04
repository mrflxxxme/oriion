# HANDOFF — current session snapshot

> Перезаписывается каждой завершённой сессией как часть Exit ritual (см. `agent-handbook/05-PR-WORKFLOW.md`). История доступна через `git log HANDOFF.md`. Журнальный лог — в `JOURNAL.md`.

## Last updated

- Date: 2026-07-04 (Phase 01.8 — auth extensions core: 2FA TOTP + magic-link + session-list)
- Session: `auto-01.8` (worktree branch `claude/auto-01.8`, **stacked on `claude/auto-01.8-mail`**, base HEAD e2c575f)
- Agent: @claude-opus (autonomous runner, ADR-037)

## Project status

- **Wave:** Wave 1 (Core MVP)
- **Phase 01.6 (Security guardrails)**: ✅ Merged (PR #84).
- **Phase 01.8-mail (Real Yandex SMTP sender)**: ✅ Code-complete on `claude/auto-01.8-mail` — pending PR + founder ack + merge.
- **Phase 01.8 (Auth extensions core)**: ✅ Code-complete on `claude/auto-01.8` (stacked on 01.8-mail) — pending PR + **founder ack** (tripwire) + merge.

## What just happened (Phase 01.8)

2FA TOTP (pyotp) + magic-link passwordless login (on the existing `EmailSender`
port, InMemory-tested) + a session-list backend, per the grill + founder-approved
decision (2026-07-03, DECISIONS-LOG). Fully autonomous, no external creds.
**OAuth (Yandex ID + VK ID) is DEFERRED to 01.8b** (needs client creds).
**This branch is stacked on `claude/auto-01.8-mail`** — the PR diff base is that
branch, NOT main.

### Commits (branch `claude/auto-01.8`, off `claude/auto-01.8-mail` e2c575f)

```
[01.8] feat(iam): TOTP + magic-link + session tables & repos (ADR-024)   [coder]
[01.8] feat(iam): 2FA TOTP + magic-link login + session-list backend      [coder]
[01.8] test(iam): 2FA TOTP + magic-link + session-list unit & integration [tester]
docs(autonomy): 01.8 phase spec + PLAN + decision log                     [reviewer]
+ evidence/ commit (adversarial_audit + docker_integration + manifest)
```

### Gap analysis (existed vs added)

- **Existed:** `iam.sessions/refresh_tokens` (+ rotation chain); the SHA-256 single-use token-table pattern (`email_verification_tokens`); the `EmailSender` port (+ `YandexSmtpEmailSender` from 01.8-mail); `session_repository.list_active_for_user`; `TokenService` (HS256 access + opaque refresh); rate-limit service; `LocalAESKMS` AES-256-GCM KMS provider.
- **Added:** 2FA TOTP (`totp_credentials` + `totp_backup_codes` tables; `TotpService` enroll/confirm/verify/disable; login second-factor challenge); magic-link (`magic_link_tokens` table; `MagicLinkService` request/consume; `send_magic_link_email` on the port + all impls); session revoke endpoints (`revoke_for_user` user-scoped + `revoke_all_others` + refresh cascade); migration `iam_0007`.

### Migration

**`iam_0007_totp_and_magic_link`** — pure-CREATE, literal DDL (via `_rls.updated_at_trigger`). Three USER-scoped tables (no cell RLS — matches the existing iam token tables; GRANT to `oriion_app`): `totp_credentials` (secret_encrypted **bytea** AES-256-GCM at rest), `totp_backup_codes` (SHA-256), `magic_link_tokens` (SHA-256). `contracts/iam/schema.sql` updated 1:1.

### How the TOTP secret is stored at rest + login gate

- **At rest:** enroll → `KMSProvider.encrypt(secret)` (LocalAESKMS AES-256-GCM) → `secret_encrypted bytea`; decrypt in-memory only. Base32 plaintext leaves the service once (enroll response), never logged. Backup codes SHA-256 hashed, single-use.
- **Login gate:** `AuthService.login` verifies password → if active 2FA, returns a short-lived HS256 `TotpChallenge` (type-guarded, no server state) with **no session minted on the password leg**; `POST /auth/login/totp` verifies challenge + a live TOTP or single-use backup code, then issues the pair. Password-only login unchanged for users without 2FA (TotpService seam defaults to None).

### New endpoints

`POST /auth/login/totp`, `POST /auth/magic-link/{request,consume}`,
`POST /users/me/totp/{enroll,confirm,disable}`,
`GET /users/me/sessions`, `DELETE /users/me/sessions/{id}`, `DELETE /users/me/sessions`.

### Gate results

```
ruff check:      All checks passed
ruff format:     clean (428 files)
mypy --strict:   Success (228 source files)
bandit -r src:   0 issues (any severity)
pytest tests/iam/unit:        116 passed, 1 live-deselected
pytest tests/iam/integration:   6 passed (real PG, testcontainers; migration 0007 applies)
src/iam coverage: 92.14% (unit+integration; gate ≥85%)
pip-audit: pyotp 2.10.0 → 0 vulns (pip/starlette findings pre-existing, not this phase)
```

### Adversarial audit (3 lenses, refute-by-default) — full JSON in evidence/

- **SECURE ✅ PASS** (0 P0/P1): TOTP secret encrypted at rest + never logged (grep + integration ciphertext assertion); tokens hashed/single-use/expiry-enforced; no 2FA bypass (challenge ≠ tokens; no session on the password leg); challenge type-guarded (a real access token is rejected); cross-user session revoke → 404 with the target row untouched; magic-link anti-enum (no oracle).
- **SOUND ✅ PASS**: second factor gates login when enabled; consumed/expired tokens → 410; backup-code replay → 401.
- **NO-REGRESSIONS ✅ PASS**: password login / verify / reset / refresh green (116 iam unit); EmailSender port extended on ALL impls; pyotp CVE-clean.

## Tripwire / founder action

- **Tripwire:** `src/iam/**` + iam migration → `auth_rbac_sessions` → PR is **NOT** auto-merge; requires **founder ack**. `db_migrations` content-check **downgrades** (0007 provably pure-CREATE; `classify_tripwire.py` confirmed).
- Founder: review + ack + merge the PR from `claude/auto-01.8`. **Base = `claude/auto-01.8-mail`** — merge 01.8-mail first (or retarget once it lands on main).

## Residual follow-ups

- **01.8b (deferred):** Yandex ID + VK ID OAuth — needs client creds.
- P3: no "regenerate backup codes" endpoint; no admin-forced-2FA tenant policy.
- P3: magic-link + TOTP-challenge live email-send depends on the deferred SMTP-creds gate (01.8-mail); flows exercised with the InMemory sender here.
- `.planning/JOURNAL.md` ~700 lines → archive older quarters to `dev-log/archive/` (maintenance, separate task).

## Next agent — read first

1. [`README.md`](./README.md) — what is this project
2. **this HANDOFF.md** — snapshot
3. [`agent-handbook/00-START-HERE.md`](./agent-handbook/00-START-HERE.md) — workflow protocol
4. [01.8 spec](./roadmap/wave-1-core-mvp/phases/01.8-auth-extensions.md) + [PLAN](./roadmap/wave-1-core-mvp/phases/01.8-PLAN.md) + DECISIONS-LOG in `_session-context/`.

## Exit ritual completed (this session)

- [x] 4 atomic commits (coder×2 + tester + reviewer) + evidence commit on `claude/auto-01.8`
- [x] DECISIONS-LOG entries (3 impl forks: TOTP at-rest KMS; login challenge; user-scoped tables)
- [x] JOURNAL.md entry appended (this date)
- [x] HANDOFF.md rewritten (this file)
- [x] Phase spec `01.8-auth-extensions.md` + `01.8-PLAN.md` written (in the WORKTREE tree)
- [x] evidence/adversarial_audit.json + docker_integration.json + manifest.json (head_sha = final non-evidence commit)
- [ ] PR opened — pending (orchestrator/founder action; tripwire needs founder ack; base = `claude/auto-01.8-mail`)
