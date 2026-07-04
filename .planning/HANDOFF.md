# HANDOFF — current session snapshot

> Перезаписывается каждой завершённой сессией как часть Exit ritual (см. `agent-handbook/05-PR-WORKFLOW.md`). История доступна через `git log HANDOFF.md`. Журнальный лог — в `JOURNAL.md`.

## Last updated

- Date: 2026-07-04 (Phase 01.8-mail — real `YandexSmtpEmailSender`)
- Session: `auto-01.8-mail` (worktree branch `claude/auto-01.8-mail`, off origin/main f7f5698)
- Agent: @claude-opus (autonomous runner, ADR-037)

## Project status

- **Wave:** Wave 1 (Core MVP)
- **Phase 01.6 (Security guardrails)**: ✅ Merged (PR #84).
- **Phase 01.8-mail (Real Yandex SMTP sender)**: ✅ Code-complete on `claude/auto-01.8-mail` — pending PR + **founder ack** (tripwire) + merge.

## What just happened (Phase 01.8-mail)

Real `YandexSmtpEmailSender` implementing the existing `EmailSender` port (prod
was `NoOpEmailSender`) over Yandex 360 SMTP via `aiosmtplib`, per the grill +
founder-approved decision (2026-07-03, DECISIONS-LOG). **Live-send is a deferred
gate** — it validates only when real SMTP creds land in the canonical `.env`
(they are NOT present now). Pre-alpha launch blocker per ADR-007 («email
verification mandatory before first task»), independent of auth-extensions/OAuth
timing.

### Commits (branch `claude/auto-01.8-mail`, off f7f5698)

```
chore(deps): add aiosmtplib for real Yandex SMTP sender (01.8)       [coder]
feat(iam): real YandexSmtpEmailSender + creds-gated selection (01.8) [coder]
test(iam): transport-mock SMTP sender + selection tests (01.8)       [tester]
docs(autonomy): 01.8-mail phase spec + PLAN + decision log           [reviewer]
+ evidence/ commit (adversarial_audit + manifest)
```

### Gap analysis (existed vs added)

- **Existed:** `EmailSender` Protocol + Console/NoOp/InMemory impls; `get_email_sender` (dev/test→Console, else→NoOp); auth_service triggers verify email; `email_verification_tokens`/`password_reset_tokens` tables (Phase 00.2); Settings + Lockbox source; per-module `tests/iam` ≥85% CI gate.
- **Added:** `YandexSmtpEmailSender` (aiosmtplib, TLS-enforced MIME); SMTP Settings fields (host/port/use_tls/user/password/from/timeout + email_verify_url_base) + `is_smtp_configured`/`smtp_sender_address` helpers; creds-gated selection (prod+creds→Yandex, prod-no-creds→NoOp fallback); `aiosmtplib>=5.1,<6.0` dep; transport-mock + selection tests + `@pytest.mark.live` smoke scaffold.

### Migration

**NONE** — purely transactional/transport phase. No new tables/columns/migrations.

### How sender selection works

`iam/deps.py::get_email_sender(settings)`:
- dev / test → `ConsoleEmailSender`.
- prod/staging **with** SMTP creds (`is_smtp_configured` = `smtp_user` AND `smtp_password` both non-empty) → `YandexSmtpEmailSender`.
- prod/staging **without** creds → `NoOpEmailSender` fallback (deferred-live-send contract; credential-less boot does NOT crash).

### Live-send validation (deferred gate — one command)

```
SMTP_LIVE_TEST_TO=you@example.com SMTP_USER=no-reply@teamly.ru \
SMTP_PASSWORD=<yandex-app-password> \
uv run --project backend pytest tests/iam/unit/test_email_service.py -m live
```

Env keys: `SMTP_HOST` (default `smtp.yandex.ru`), `SMTP_PORT` (465), `SMTP_USER`,
`SMTP_PASSWORD` (Yandex **app-password**), `SMTP_FROM` (opt), `SMTP_USE_TLS`
(opt, default true), `SMTP_LIVE_TEST_TO`. Prod: put `SMTP_USER`+`SMTP_PASSWORD`
in Lockbox/`.env` → selection auto-switches NoOp→Yandex (no flag needed).

### Gate results

```
ruff check:      All checks passed
ruff format:     clean (419 files)
mypy --strict:   Success (224 source files)
bandit -r src:   0 issues (any severity)
pytest tests/iam: 87 passed, 1 live-skipped
email_service.py coverage: 100%
tests/iam aggregate: 88.28% (gate ≥85%)
pip-audit: aiosmtplib 5.1.2 → 0 vulns (pip/starlette findings pre-existing, not this phase)
```

### Adversarial audit (3 lenses, refute-by-default)

- **SECURE ✅ PASS** (0 P0/P1): token never logged (caplog test) / never persisted; TLS actually enforced (implicit 465 / STARTTLS `start_tls=True` before AUTH — no plaintext-auth over cleartext); cert-verify at ssl default (never disabled); `smtp_password` is SecretStr.
- **SOUND ✅ PASS**: MIME built correctly for both methods + url_base link mode; send failure propagates (no silently-swallowed "sent").
- **NO-REGRESSIONS ✅ PASS**: existing email/auth tests green; NoOp fallback preserved; new dep CVE-clean.

## Tripwire / founder action

- **Tripwire:** touches `src/iam/**` → `auth_rbac_sessions` classification → PR is **NOT** auto-merge; requires **founder ack**.
- Founder: review + ack + merge PR from `claude/auto-01.8-mail`. Note deferred live-send (not validated until SMTP creds provisioned).

## Residual follow-ups

- **Live-send gate (deferred):** validate real delivery via the one command above once SMTP creds land in canonical `.env`/Lockbox.
- Optional: HTML multipart emails (currently plaintext) — low priority.
- `.planning/JOURNAL.md` >300 lines → archive to `dev-log/archive/JOURNAL-2026Q3.md` (maintenance, separate task).

## Next agent — read first

1. [`README.md`](./README.md) — what is this project
2. **this HANDOFF.md** — snapshot
3. [`agent-handbook/00-START-HERE.md`](./agent-handbook/00-START-HERE.md) — workflow protocol
4. [01.8-mail spec](./roadmap/wave-1-core-mvp/phases/01.8-mail-smtp-sender.md) + DECISIONS-LOG in `_session-context/`.

## Exit ritual completed (this session)

- [x] 4 atomic commits (coder×2 + tester + reviewer) + evidence commit on `claude/auto-01.8-mail`
- [x] DECISIONS-LOG entry (impl fork: SMTP TLS default)
- [x] JOURNAL.md entry appended (this date)
- [x] HANDOFF.md rewritten (this file)
- [x] Phase spec `01.8-mail-smtp-sender.md` + `01.8-mail-PLAN.md` written
- [x] evidence/adversarial_audit.json + manifest.json
- [ ] PR opened — pending (orchestrator/founder action; tripwire needs founder ack)
