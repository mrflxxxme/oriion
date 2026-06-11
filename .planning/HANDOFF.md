# HANDOFF — current session snapshot

> Перезаписывается каждой завершённой сессией как часть Exit ritual (см. `agent-handbook/05-PR-WORKFLOW.md`). История доступна через `git log HANDOFF.md`. Журнальный лог — в `JOURNAL.md`.

## Last updated

- Date: 2026-06-11 (Phase 00.7 Frontend skeleton **COMPLETE** + live-validation Exit ritual.)
- Session: `romantic-hamilton-4b43c5`
- Agent: @claude-opus

## Project status

- **Wave:** Wave 0 (Foundation) — **closing**. All build phases complete (incl. the frontend now) + architecture live-validated. The only remaining Wave-0 item is the **founder staging 10× anchor run** (gate D5) — a Wave-0→Wave-1 gate.
- **Phase 00.1–00.5b**: ✅ Complete (see git history / prior HANDOFFs).
- **Phase 00.6 PR-A + PR-B**: ✅ Complete ([#36](https://github.com/mrflxxxme/oriion/pull/36), [#38](https://github.com/mrflxxxme/oriion/pull/38), [#39](https://github.com/mrflxxxme/oriion/pull/39)) — backend architecture proven end-to-end with real LLMs.
- **Phase 00.7 (frontend skeleton)**: ✅ **Complete** (this session; C0–C16). UI built on the proven API + **live-validated end-to-end**.
- **Phase 01.1 retro (Wave-1 hardening)**: ⏳ Pending — `roadmap/wave-1-core-mvp/phases/01.1-retro.md` holds AC-W1-1..23 (+ now the 00.7 deferred polish, see below).

## Active blockers

| ID | Описание | Owner | Block уровень |
|---|---|---|---|
| OQ-04 | РКН-уведомление оператора ПДн | Founder + юрист | Submitted — dev unblocked; final РКН до prod-launch |
| OQ-02 | Юр.форма ООО vs ИП | Founder | НЕ блокирует тех.разработку; до ЮKassa (Wave 1) |

## What just happened — Phase 00.7 (C0–C16)

Built the **functional Wave-0 demo UI** (Vite 6 + React 19 + TanStack Router/Query + Tailwind v4 + Radix/shadcn pattern) on top of the proven 00.6 API, and **proved the whole click-path end-to-end against the live docker stack with real LLMs**.

### Commit ledger

| # | Commit |
|---|---|
| C0 | pre-flight: pin live API truth + Vite proxy + SSE/run fixtures |
| C1 | deps + tooling (query/zustand/rhf/zod/radix/markdown + playwright/axe/jest-axe) |
| C2 | design tokens + dark/light theme (Nordic Warm) |
| C3+C4 | 18 UI primitives (component-inventory) + barrel |
| C5+C6 | API client (apiFetch + zod) + auth store + single-flight 401 refresh |
| C7 | code-based router + providers + boot-time silent session restore |
| C8 | auth feature (Login/Register, FZ-152 consent, auto-login) |
| C9 | cells feature (list + detail, workspace fan-out) |
| C10 | task submit (generic form + «Маркет-бриф» preset, create→navigate→fire /run un-awaited) |
| C11 | SSE fetch-reader + pure progress reducer (9 event types) |
| C12 | task result page (Tabs: progress cards + log / markdown artifacts / cost) |
| C13 | Playwright E2E (@live demo + backend-free smoke) |
| C14 | CI gates (token §A/§B grep + AC5 barrel audit + playwright job) |
| C15 | 3-agent frontend audit fixes (a11y contrast, single-accent, mobile nav, markdown) |
| C16 | Exit ritual |

### Live validation (2026-06-11) — UI demo PROVEN

`wave-0-demo.spec.ts` (@live) drove the real flow in Chromium against the docker stack: **register → auto-login → cells → cell → submit «Маркет-бриф» → SSE 3-agent progress (Исследователь→Аналитик→Райтер) → 3 markdown artifacts (matrix/analysis/brief) → axe 0 serious/critical on all 5 routes. PASS, ~2.3-2.4min.**

Two real bugs were caught by the live run that mocked unit tests missed:
1. **Auth token-store ordering** — `/users/me` was called before the access token was written to the store → 401 → failed refresh → silent register failure. Fixed: persist tokens before the authed call. (Lesson: keep a live, non-mocked E2E — mocks can't catch token plumbing.)
2. **Button a11y contrast** — destructive/cta buttons used theme-flipping `text-page` (3.8:1 dark-on-rose). Fixed with mode-invariant `text-on-cta`/`text-on-danger` tokens. The 3-agent audit also caught the same class on feedback Badges (fixed in C15).

### Acceptance — 11/12 PASS, AC4 by-design

AC1 (773ms), AC2 (5 routes), AC3 (@live demo), AC5 (18 components), AC6 (token grep), AC7 (axe×5 routes), AC8 (dark/light), AC9 (tsc strict), AC10 (91.8% cov), AC11 (9 SSE types), AC12 (FZ-152) — all ✅. AC4 (SSE <200ms) satisfied by design (synchronous reducer; per-token is Wave-1). **AC7 (UI-demo) unblocked.**

### Spec amendments (live-driven — flag for architect)

1. No flat `GET /cells` — list = `GET /workspaces` → `GET /workspaces/{id}/cells`.
2. SSE auth = Bearer header → hand-rolled fetch+ReadableStream reader (EventSource can't).
3. TS types from live `/docs`, not openapi-typescript off draft contracts (contracts drift).
4. Code-based TanStack Router (not file-based codegen).
5. Three-step task flow: `POST /tasks` → `POST /run` (blocking) → `GET /stream` (drain-replay); UI fires /run un-awaited.

### Deferred → Wave-1 (`01.1-retro.md` + `revisions/00.7-audit-deferred.md`)

i18n key-completeness (Wave-0 placeholder mode allowed), refresh-token zod parity, textarea counter aria-live debounce, minor a11y polish (sort-button name, pagination aria-disabled, single-tab Tabs), design nits (mono numerics, card elevation, sidebar hover, gap rhythm), per-page designer loop re-expansion.

## Local dev / demo runbook (for the founder to click-test live)

1. Start the stack: `docker compose -f infra/docker-compose.staging.yml -f infra/docker-compose.staging-local.override.yml --env-file backend/.env up -d --build` (backend on :8000).
2. Refresh the Yandex IAM token when failover is needed: `yc iam create-token` → update `YANDEX_IAM_TOKEN` in `backend/.env` → `docker compose ... up -d backend`. (DeepSeek is primary + funded; Yandex is failover; GigaChat fails TLS locally — AC-W1-21.)
3. Frontend: `cd frontend && npm install && npm run dev` → http://localhost:5173 (Vite proxies `/api` → :8000).
4. Full automated proof: `npm run e2e:live` (real ~2.3min run) or `npm run e2e:ci` (fast backend-free smoke).

## Keys / config state (local `backend/.env`, gitignored — NEVER in git)

`DEEPSEEK_API_KEY` funded/primary. `YANDEX_IAM_TOKEN` ~12h TTL (refresh via `yc`). `BRAVE_SEARCH_API_KEY` live. `GIGACHAT_AUTH_KEY` present but TLS fails in-container (AC-W1-21). `REQUIRE_EMAIL_VERIFICATION=false` locally.

## Carryover — read order for the next session

1. `README.md` → 2. **this HANDOFF.md** → 3. `STATUS.md` → 4. `agent-handbook/00-START-HERE.md` → 5. for Wave-1: `roadmap/wave-1-core-mvp/phases/01.1-retro.md` + `revisions/00.7-audit-deferred.md`.

## Exit ritual (this session)

- [x] HANDOFF.md rewritten — Phase 00.7 complete + live validation
- [x] STATUS.md updated — Phase 00.7 ✅, AC7 unblocked
- [x] phase-spec 00.7 status → Complete + AC1–AC12 evidence + spec amendments
- [x] JOURNAL.md appended — 00.7 closure entry
- [x] `revisions/00.7-audit-deferred.md` — audit dispositions
- [ ] Wave-0 anchor flip — pending founder staging 10× (Track A, independent)
