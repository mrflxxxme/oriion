# API notes — pinned against the live backend (Phase 00.7 C0 pre-flight)

> Captured 2026-06-10 against the local docker-compose staging stack
> (`http://localhost:8000`, `/api/v1` prefix). These are the **factual**
> shapes the frontend is built on — they override the draft `contracts/*`
> wherever the two diverge. Fixtures live in `src/test/fixtures/`.

## Base + transport

- Base URL: `/api/v1` (Vite dev proxy `/api` → `http://localhost:8000`; backend has **no CORS middleware**).
- Auth: `Authorization: Bearer <access_token>` on every protected call **including the SSE stream** (native `EventSource` can't set headers → hand-rolled fetch+ReadableStream reader).
- Errors: RFC 7807 `application/problem+json` with a `code` field (e.g. `iam.consent.pdn_missing`). Validation errors (422) use FastAPI `{detail: [{loc, msg, type}]}`.
- Email validation rejects reserved TLDs like `.test` → use `.dev`/real domains in fixtures & E2E.

## Auth (iam)

| Call | Shape |
|---|---|
| `POST /auth/register` | body `{email, password(≥12), display_name?, locale, consent_pdn(must be true), consent_marketing?}` → **201** `{user_id, workspace_id, cell_id, email, email_verification_sent}` |
| `POST /auth/login` | body `{email, password}` → **200** `{access_token, refresh_token, expires_in: 900, token_type: "Bearer"}` |
| `POST /auth/refresh` | body `{refresh_token}` → **200** same `TokenPair` (rotation) |
| `POST /auth/logout` | body `{refresh_token}` → **204** |
| `GET /users/me` | → `{id, email, email_verified_at, display_name, locale, timezone, created_at, updated_at}` |

- `REQUIRE_EMAIL_VERIFICATION=false` locally → register, then login immediately (no verify step). Register already provisions workspace + cell + agent team.
- Access TTL = 900s. consent_pdn missing → 422 `iam.consent.pdn_missing`.

## Multitenancy (cells)

- **No flat `GET /cells` list.** List path is: `GET /workspaces` → `{items: Workspace[], next_cursor}`, then per workspace `GET /workspaces/{workspace_id}/cells` → `{items: Cell[], next_cursor}`.
- `GET /cells/{cell_id}` → `CellOut {id, workspace_id, slug, display_name, vertical_template_slug, settings, created_at, updated_at, archived_at}`.
- In Wave-0 a fresh user has exactly **1 workspace + 1 cell** (auto-provisioned at register).

## Tasks — three-step flow

1. `POST /api/v1/cells/{cell_id}/tasks` — body `{title(≤255), prompt(≥1), description?, parent_task_id?}` → **202** `TaskOut` (`status: "queued"`). NB: field is **`prompt`**, not `input_jsonb`.
2. `POST /api/v1/cells/{cell_id}/tasks/{task_id}/run` — **blocking** (real LLM orchestration; observed 71–170s). → **202** `{task_id, status: "succeeded"|"failed", result: CoordinatorOutput}`. Without this call the SSE stream stays empty.
3. `GET /api/v1/cells/{cell_id}/tasks/{task_id}/stream` — SSE, drain-replay (buffered events replayed to a late subscriber, EOF after the terminal event). Opening it **before** `/run` and after work has started both yield the full ledger.
4. `GET /api/v1/cells/{cell_id}/tasks/{task_id}` → `TaskOut` (poll fallback). `POST .../cancel` → cancel.

`TaskOut`: `{id, cell_id, parent_task_id, agent_instance_id, initiated_by_user_id, title, description, status, priority, started_at, completed_at, total_cost_credits (string-decimal), total_input_tokens, total_output_tokens, created_at}`.

## SSE wire format (Wave-0 = 8 coarse events)

Frames are `event: <type>\ndata: <json>\n\n`. Observed sequence for a Market-brief run:

```
event: task.started
data: {"started_at":"2026-06-10T17:46:50.088668+00:00"}

event: task.delegation_started
data: {"target_agent_slug":"researcher"}

event: task.delegation_completed
data: {"target_agent_slug":"researcher","sub_task_id":"<uuid>","cost_credits":"0.480936","tokens_used":2490}

  … (repeats for "analyst", then "writer") …

event: task.completed
data: {"result": <CoordinatorOutput>}
```

- Agent slugs (fixed Wave-0 ScriptedCoordinator order): **`researcher` → `analyst` → `writer`**.
- Terminal events: `task.completed` | `task.failed` | `task.cancelled`. `task.completed.data.result` carries the **full CoordinatorOutput incl. artifacts** — the result tab can be populated straight from the terminal SSE event; no extra fetch needed.
- `cost_credits` / `total_cost_credits` are **string-decimals** — parse with care.
- Contract lists 9 types incl. `task.step_token` / `task.step_started` / `task.step_completed` — these are **Wave-1** (per-token streaming, AC-W1-16/23) and are NOT emitted in Wave-0. The progress reducer must tolerate them (AC11) but renders the 3 coarse agent cards from the delegation events.

## Artifacts (3 markdown strings)

`CoordinatorOutput` = `{summary, delegation_plan: [], citations: [], artifacts: Artifact[], total_cost_credits}`.

`Artifact` = `{id, type, path_or_inline}` — **only these 3 keys** (no `storage_kind`/`mime_type` in the run output). `type ∈ {matrix, analysis, brief}`; `path_or_inline` is the **inline markdown string** (Wave-0 always inline). The `brief` artifact contains BOTH the market brief and the 10-post content plan (`### Пост N — <channel> — <day>` headings). Render with `react-markdown` + `remark-gfm` (matrix is a GFM table) — never `dangerouslySetInnerHTML`.

## Notes that shaped the build

- `/run` latency exceeds the 120s AC8 cap when DeepSeek is slow / fails over (YandexGPT 5.1 Pro, then GigaChat). That's a Wave-1 tuning concern (AC-W1-22/23), not a UI concern — the UI just renders whatever arrives and shows a live timer.
- GigaChat fails locally with `SSL CERTIFICATE_VERIFY_FAILED` (RU Trusted Root CA absent in container — AC-W1-21); YandexGPT needs a fresh `yc iam create-token` (~12h TTL). Neither blocks the UI as long as DeepSeek (primary) is funded.
