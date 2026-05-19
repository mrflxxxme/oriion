# Section 05 — Roadmap / Product-vision alignment audit

**Auditor:** Product Manager (Alex)
**Date:** 2026-05-19
**Branch:** `claude/heuristic-rhodes-f7a3ef` (Phase 00.2.5 code-complete, pre-Phase-00.5)
**Scope:** Wave-0 vision-to-code alignment, dual-messaging USP fidelity, 5-vertical trajectory, РФ-compliance baseline, target-date feasibility.

---

## Top-level verdict: **FLAG** (proceed with eyes open — no structural blockers, but 5 in-loop items must be closed during Phase 00.5)

Wave-0 infrastructure is **on-vision**. The five biggest decisions — DeepSeek primary with Yandex/GigaChat failover, RU-currency triad, FZ-152 consent ledger, ru-RU/Europe/Moscow defaults, multitenancy with `workspace`/`cell` rename — are all present in code, not just docs. The dual-messaging "horizontal + vertical" architecture is preserved: the horizontal Coordinator/Researcher/Writer/Analyst is the Wave-0 anchor, the Master-Agent layer is scoped to Wave-1+ and the contracts (`agents`, `tasks`, `role-prompts/`) reserve the seams without forcing scope.

What earns the FLAG (not PASS): the **anchor demo itself is not yet runnable end-to-end through HTTP**. `src/main.py` still wires only the iam routers; LLM / multitenancy / MCP routers return 501. That is exactly what Phase 00.5 is supposed to fix, and the gap is documented in HANDOFF.md:80 and pinned by `test_llm_chat_endpoint_is_not_yet_wired`. The product question is whether Phase 00.5 can wire **and** ship the 4-agent Pydantic-AI runtime **and** the demo scenario **and** land Phase 00.6 in **21 calendar days** to hit the 2026-06-09 Wave-0-complete target. Velocity to date supports it, but the margin is thin (see §10 Target-date feasibility).

No vision-to-code traceability gaps were found that would lock out any of the 5 verticals or any Wave-2-4 deliverable (Pixel Department, Mini App, Stars billing). Two items deserve in-loop attention during Phase 00.5: `accounting_ip` data-shape readiness (no contract artefact yet for financial integrations — pure Wave-3 by spec, but the `cells.settings_jsonb` JSONB column is the only current extension point, so verify the seam is intentional), and the per-vertical contract scaffolding promised by ADR-029 (Master-Agent prompts directory).

---

## 1. Wave-0 anchor target alignment — gap analysis

### Anchor target (per STATUS.md:10 + PROJECT.md:7 + roadmap/wave-0-foundation/PHASES.md:25)

> Internal demo: horizontal `productivity-core` team end-to-end with the «Market & content brief» scenario — Coordinator + Researcher + Writer + Analyst, 3 parallel sub-task delegations, 3 artefacts (brief.md ≥1500w + competitive-matrix.md ≥5×4 + content-plan.md = 10 posts), p95 ≤ 120s, cost ≤ 30¢ per run.

### What's in code today (post 00.1+00.2+00.3+00.4+00.2.5)

| Anchor capability | Code state | Verdict |
|---|---|---|
| Register → login → tokens (full auth) | ✅ Real implementation, 5-test E2E suite against testcontainers PG passes. `iam` 87% unit coverage. | **DONE** |
| Workspace + cell provisioning at register | ✅ `provision_initial_workspace` wired into `AuthService.register` (stub deleted in 00.2.5). | **DONE** |
| Consent ledger (FZ-152 invariant 6) | ✅ `iam.consents` (version-pinned, append-only, kind ∈ {pdn, marketing, tos}), `RegisterRequest.consent_pdn=true` mandatory else 422. | **DONE** |
| Audit log with partitioning | ✅ `audit.audit_log` RANGE-partitioned by `ts`, two seeded months + default catch-all, append-only trigger, 3-year retention contract. | **DONE** |
| LLM gateway core (provider abstraction) | ✅ `LLMRouter` + DeepSeek → Yandex → GigaChat failover chain + circuit breakers. | **DONE** |
| BYOK encryption | ✅ `KMSProvider` (LocalAESKMS Wave-0, Yandex KMS placeholder Phase 00.6); `byok_proxy.py` OpenAI-shape forwarder. | **DONE** |
| Cost ledger (3-currency triad) | ✅ `llm_usage_log{cost_usd, cost_rub, fx_rate_usd_to_rub}` + `credit_transactions{amount_rub, fx_rate_usd_to_rub}`, atomic write, append-only triggers, invariant `SUM(credit_transactions.amount_rub) == SUM(llm_usage_log.cost_rub)` per cell verified by `test_cost_ledger_sum_match.py`. | **DONE** |
| RLS isolation (3-GUC layered) | ✅ `_shared.current_user_id() / current_workspace_id() / current_cell_id()` helpers; write policies on all 3 multitenancy tables; default-deny holds without GUC. | **DONE** |
| **Coordinator-style flow (Pydantic-AI runtime)** | ❌ **NOT BUILT** — Phase 00.5 scope. No `backend/src/agents/`, `backend/src/tasks/`, `backend/src/runtime/` directories. | **GAP** |
| **`/api/v1/llm/chat` returns LLM response end-to-end** | ❌ Router exists, handler is 501. `src/main.py` does not wire LLM/multitenancy/MCP routers. Phase 00.5 owns this. | **GAP** |
| **Cost ledger row written during demo flow** | ⚠️ Atomic-write contract exists + tested at service-tier (`test_cost_ledger_sum_match.py`), but the demo path through HTTP doesn't reach it until 00.5 wires the LLM router. | **CONDITIONAL** |
| **3 artefacts written to cell.memory** | ❌ NOT BUILT — Phase 00.5 scope; `cell_<uuid>.memory_entries` table is provisioned by 00.3 but no agent writes it yet. | **GAP** |
| Role-prompts for 4 horizontal roles | ✅ `contracts/role-prompts/coordinator.md` exists (frontmatter `role_id: coordinator`, `preset: productivity-core`). Sample check confirms structured prompt files. | **DONE (skeleton)** — Phase 00.5 needs to verify all 4 (coordinator/researcher/writer/analyst) exist + 9-section structure validated by `role_prompt_loader`. |

### Phase 00.5 critical path (what must ship to make the anchor demo real)

1. **`backend/src/main.py` router assembly** — include multitenancy + LLM + MCP routers under `/api/v1`; install `MultitenancyError` handler.
2. **Provider DI** — instantiate `DeepSeekProvider`, `YandexGPTProvider`, `GigaChatProvider`, `LocalAESKMS` inside FastAPI lifespan; expose `get_llm_router()` dependency.
3. **Pydantic-AI runtime** — `agents/{coordinator,researcher,writer,analyst}.py` + `tools/delegate.py` + `runtime/orchestrator.py` + `runtime/sse_publisher.py` + `runtime/budget_guard.py`. Per phase-spec 00.5.
4. **Tasks bounded context** — `tasks/models.py` + `tasks/services/{task_service,cost_rollup_service}.py` + `tasks/routers/{tasks,stream}.py`. Migrations `tasks/0001..0003`.
5. **Agents bounded context** — `agents/models.py` (archetypes + team_presets + agent_instances) + provisioning service + `productivity_core_v1` seed. Migrations `agents/0001..0003`.
6. **Role-prompt loader** — parse 9-section structure from `contracts/role-prompts/*.md`.
7. **SSE event-types** — 9 event types from phase-spec.
8. **Demo runner script** — `backend/scripts/demo_market_brief.py` end-to-end, assert artefact contracts.
9. **Live LLM provider tests** — populate `@pytest.mark.live` suite (declared but empty per HANDOFF.md:129).
10. **`test_llm_chat_endpoint_is_not_yet_wired`** retired and replaced with register → chat → cost-ledger E2E.

### Is the gap size realistic for 2026-06-09?

**Conditional yes.** See §10 below — velocity supports it, but everything must go right.

---

## 2. Dual-messaging USP fidelity (PROJECT.md)

> "Универсальная команда + РФ-вертикали поверх" — horizontal as entry-point, 5 verticals via Master-Agent layer.

### Horizontal path (Wave 0)

| Element | State | Evidence |
|---|---|---|
| `productivity-core` preset slug | ✅ Reserved in `contracts/role-prompts/coordinator.md` (`preset: productivity-core`). | Read sample |
| 4-role bundle (Coord + Researcher + Writer + Analyst) | ✅ Defined in phase-spec 00.5; deep role-prompts contract type established. | `roadmap/wave-0-foundation/phases/00.5-pydantic-ai-productivity-team.md:7-11` |
| `cells.vertical_template_slug NULL` for horizontal | ✅ Model allows NULL, index excludes NULL rows from vertical-only queries. | `backend/src/multitenancy/models.py:114` |
| Top-level orchestration via Coordinator (no Master) | ✅ ADR-029 explicit: horizontal stays single-layer; Master-Agent only verticals. | `ADR-029-master-agent-vertical-templates.md:39-45` |

### Vertical path (Wave 1+) — foundation extensibility

| Element | State | Evidence |
|---|---|---|
| Master-Agent layer ADR exists with cost+latency budget | ✅ ADR-029 with +1 LLM-call, +15-20% tokens, +1-3 sec latency, per-task 50 T-credit cap. | `ADR-029:77-82` |
| R-32 (Master-Agent cost overhead) tracked | ✅ Risk register entry with mitigation = phase-01.1 AC. | `risks/REGISTER.md:194-200` |
| `cells.vertical_template_slug` column reserved | ✅ Text column, indexed, NULL allowed. | `models.py:114` |
| Per-vertical role-prompt directory structure planned | ⚠️ ADR-029 mentions `contracts/role-prompts/masters/<vertical>.md` but the directory does not yet exist. Acceptable — Wave-1 scope per ADR-029. | `ADR-029` |
| Vertical-specialist slot in cell schema | ✅ `agents.agent_instances.archetype_id` FK with no vertical lock-in. | `contracts/agents/schema.sql` (read header) |

**Verdict — boundary is clean.** Wave-0 has not shipped any vertical-specific code, and the seams for the Master-Agent layer + per-vertical specialists are reserved without scope creep. Phase 00.5 has the option to scaffold a `contracts/role-prompts/masters/` directory with a single skeleton file as a "proof of extensibility" but it is not required for Wave-0.

---

## 3. 5-vertical trajectory (Wave-1+) — lock-out check

| Vertical | Wave | Critical capability | Wave-0 risk? |
|---|---|---|---|
| Marketing-agency RU | W1 | Telegram-mcp (Read+post+Business API) | **NO LOCK-OUT** — mcp contract is SKELETON (`contracts/mcp/README.md:5`), code under `backend/src/mcp/` exists as scaffolding (`read_url` built-in tool + connection_service). Adding Telegram MCP adapter Wave-1 is additive. |
| Telegram-крейтор | W1 | Telegram MCP + Business API consent UX | **NO LOCK-OUT** — same as above + OQ-32/OQ-33 already opened for privacy/РКН-update flow. |
| WB-Селлер | W2 | Pyodide in-browser Python + WB Партнёры MCP | **NO LOCK-OUT** — Pyodide is a frontend concern (no W0 frontend code committed; verified by repo state — only `backend/` + `frontend/` skeleton from 00.1). R-27/R-28 already log Pyodide risks. |
| ИП-Бухгалтерия | W3 | 1С / Эльба integration + accounting data shape | **WATCH** — no existing contract artefact for financial transaction data shape. The only Wave-0 extension point is `cells.settings_jsonb` (multitenancy.cells:settings_jsonb JSONB). That is intentional per ADR-024 (per-vertical settings live in JSONB until contract is needed Wave-3), but worth flagging that there is no current contract that "shape-locks" against future accounting integration. **In-loop in Phase 00.5: confirm Phase 00.5 brief does not write any vertical-specific schema that would constrain ИП-Бух data flow.** |
| СМБ-Sales | W3 | Bitrix24 / amoCRM MCP | **NO LOCK-OUT** — same mcp-skeleton story as Marketing/Telegram. |

**Verdict — no Wave-0 decision locks out any vertical.** The `cells.settings_jsonb` + `vertical_template_slug` pattern + mcp skeleton + agent_archetype FK are precisely the right shape for "horizontal + 5 verticals added later" without forking schema.

---

## 4. РФ-compliance baseline (FZ-152 + РКН + data residency)

| Requirement | State | Evidence |
|---|---|---|
| Consent ledger version-pinned + append-only | ✅ `iam.consents.version` mandatory; `ConsentService.record` pins `self._version`; revoke writes new row (no UPDATE). | `iam/services/consent_service.py:33,49`; `CONSENT_VERSION_CURRENT=2026-05-17` in `.env.example:46` |
| Audit log retention partitions | ✅ Monthly partitions May/June 2026 + default catch-all; 3-year retention via partition DROP (not DELETE — would be blocked by append-only trigger). | `migrations/versions/audit/0001_audit_log_partitioned.py:8-16` |
| Locale default `ru-RU` | ✅ `iam.users.locale` default `'ru-RU'`. | `iam/models.py:69` |
| Timezone default `Europe/Moscow` | ✅ `iam.users.timezone` + `multitenancy.workspaces.timezone` both default `'Europe/Moscow'`. | `iam/models.py:71`; `multitenancy/models.py:70-71` |
| Country code default `RU` | ✅ `multitenancy.workspaces.country_code` default `'RU'`. | `multitenancy/models.py:68` |
| Data residency (Yandex Cloud ru-central-1) | ⚠️ **Phase 00.6 scope** — env placeholders `YC_FOLDER_ID`, `YC_SERVICE_ACCOUNT`, `YC_OBJECT_STORAGE_BUCKET`, `YANDEX_CLOUD_KMS_KEY_ID` all present in `.env.example:60-80`. Code defaults all dev to localhost. **No risk** — placeholder pattern is correct. |
| Anti-enumeration on forgot/resend | ✅ Always-202 contract per architect-PR amendment (`contracts/iam/api.yaml`); verified by phase-spec 00.2. | STATUS.md:58 |
| RKN notification (OQ-04) | ✅ Submitted; final confirmation pre-prod-launch. Dev unblocked. | STATUS.md:67 |
| FZ-152 cross-border consent (DeepSeek) | ✅ ADR-018:79-83 documents client consent requirement + ru-only `stack_preference` flag for regulated sectors. | `ADR-018:79-83` |

**Verdict — baseline is in place.** No FZ-152 gap. The only watch-item is Phase 00.6 ensuring all production traffic terminates in ru-central-1 (already in scope).

---

## 5. 3-tier LLM strategy (ADR-018) — code-vs-contract check

| ADR-018 requirement | Code state | Verdict |
|---|---|---|
| DeepSeek → YandexGPT → GigaChat failover chain | ✅ `router_service.py:32` `_CHAT_CHAIN = ("deepseek", "yandexgpt", "gigachat")` + circuit-breaker integration. | **PASS** |
| RU-currency triad in `llm_usage_log` | ✅ `cost_usd numeric(10,6) + cost_rub numeric(12,4) + fx_rate_usd_to_rub numeric(10,6)` + atomic-write contract. | **PASS** |
| BYOK OpenAI-compatible | ✅ `byok_proxy.py:28` registers `openai` + `anthropic` (Wave-0 OpenAI-shape only; Anthropic native API Wave-2+ per `byok_proxy.py:8-9`). | **PASS** |
| BYOK supports 5+ providers (DeepSeek/Yandex/GigaChat/OpenAI/Anthropic per ADR-008:56) | ⚠️ `_BYOK_BASE_URLS` registers only `openai` + `anthropic`. DeepSeek BYOK would go through the managed-DeepSeek path (same endpoint, customer key); Yandex/GigaChat BYOK Wave-1+. **No locks** but worth confirming the BYOK CRUD path tolerates `provider_slug='deepseek'` ([ADR-008] tariff matrix promises all 5). | **WATCH** |
| `FX_RATE_USD_TO_RUB` env-configurable | ✅ `.env.example:86` `FX_RATE_USD_TO_RUB=100.0`; `pricing_service.py:25` reads from env. No hardcoded magic number. | **PASS** |
| `ROLE_TO_MODEL` mapping for Wave-0 agents | ✅ `router_service.py:23-28` includes coordinator (deepseek-reasoner) + specialist (deepseek-chat) + embedder (yandexgpt). | **PASS** |
| Role-level routing for analyst/writer/researcher | ⚠️ ADR-018:51-63 has a richer mapping (coordinator → R1, writer/researcher → V3, analyst → R1, accountant → yandex-pro). Wave-0 collapse to `coordinator/specialist/embedder/default` means Phase 00.5 owns the per-role-key expansion. **NOT A BLOCKER** — current routing handles the demo (coordinator → R1, all others → specialist → V3). | **WATCH** |

**Verdict — PASS with two WATCH items.** Both deferrals are documented and Phase-00.5/01.1 scope.

---

## 6. Pixel Department / Mini App / Stars billing trajectory — W0 lock-out check

| Future capability | Wave | W0 lock-out risk |
|---|---|---|
| **Pixel Department** (2D Canvas + drag/drop) | W2 | **NO** — no frontend code committed; `frontend/` skeleton from Phase 00.1 only; ADR-021 (AI-generated pixel pipeline) preserves W2 scope. |
| **Telegram Mini App** (WebApp) | W2 | **NO** — iam consent flow currently email-based, but `iam.consents.kind ∈ {pdn, marketing, tos}` is open-ended (consent kind is a Literal not enforced as enum at DB level — could extend to `telegram_business`). Phase 02.X can add a new consent kind without breaking the ledger. **In-loop check during Phase 00.5: when role-prompt loader is built, do not hard-code `kind` to a closed set if it touches DB schema; leave the open-ended Text column intact.** |
| **Telegram Stars billing** | W4 | **NO** — `credit_transactions.amount_rub` is the only currency column today, but `provider` (text, nullable, line 60) is an open extensibility hook. Stars billing in W4 can add a sibling `credit_transactions.amount_stars` column (additive migration) or rely on `provider='telegram_stars'` + pricing_table conversion. No W0 decision constrains this. |

**Verdict — clean.** All three W2-4 deliverables have open extension points and no W0 commitment forces a rewrite.

---

## 7. Risk register cross-check

| Risk | W0 controls deployed | W1+ gaps to watch |
|---|---|---|
| **R-04 (runaway costs)** | Per-task 50 T-credit cap planned for Phase 00.5 budget_guard.py + 3-currency cost ledger + append-only triggers preventing tampering. | Live spend-rate threshold + dashboard ETL = W1+; per-cell daily cap = W1 billing wiring. |
| **R-05 (data leak)** | Cell-level RLS (3-GUC layered) + workspace isolation policies + BYOK encryption (KMSProvider) + audit log immutable + secrets-scanning CI (gitleaks + trufflehog) deployed Phase 00.1. | DLP scanner on MCP tool output = W2+ (with first real MCP servers); pen-test = W2. |
| **R-08 (regulatory)** | RU-locale defaults + RKN-submitted + consent ledger version-pinned + audit retention partitions. | Quarterly legal review process not yet operational (founder + retained юрист = W1+); товарный знак = W2. |
| **R-11 (retention/churn)** | N/A for Wave-0 (no users yet). | TTFV instrumentation = Phase 00.6 deploy/observability; Health Score = W2-3. |
| **R-12 (scope creep)** | Phase-spec discipline maintained (00.1 → 00.2 → 00.3+00.4 combined PR → 00.2.5 integration); no phase has shipped scope outside its phase-spec. Each PR has had its own audit. | **No structural gap** — process is the control. |

**New risks introduced by W0 implementation choices NOT in the register:**

- **R-NEW-1 (Wave-0 BYOK provider coverage gap):** `_BYOK_BASE_URLS` Wave-0 covers only `openai` + `anthropic`. ADR-008:56 promises 9-provider BYOK by tariff matrix. If a Wave-1 early friend wants DeepSeek BYOK, the current `byok_proxy.py` does not route DeepSeek as a BYOK upstream (only as a managed primary). **Severity: low. Mitigation: Phase 00.5 to verify `byok_service.create_key(provider='deepseek')` path exists OR document deferral to Phase 01.x.**
- **R-NEW-2 (Sanctioned cross-context import):** `llm_gateway/services/billing_service.py:26` imports `billing.models.CreditTransaction` — violates ADR-024 bounded-context isolation. Sanctioned in PR #30 audit (H1) per llm-gateway README invariant #7 (atomic 3-currency write). **Severity: low. Mitigation: ADR-024 amendment to formalize the sanctioned exception (item A-12 in post-merge audit); refactor to outbox/port pattern W1+.**
- **R-NEW-3 (Legacy `organization_id` term drift):** `contracts/mcp/schema.sql:8/18/30/38/56/69` + `contracts/rbac/schema.sql:90/148/156-158` + `billing/events.yaml:13/31` + 3 contract READMEs still reference `organization` in comments/skeleton SQL. Code is clean (`workspace` everywhere). **Severity: low (doc-only). Mitigation: M-4 from post-merge audit, deferred docs PR or Phase 00.6.**

---

## 8. Open-questions cross-check

| OQ | Status in OPEN-QUESTIONS.md | Reality check | Verdict |
|---|---|---|---|
| OQ-04 (РКН) | Submitted | Submitted; mock-data in dev/test; final confirmation pre-prod | ✅ Consistent |
| OQ-13/14/15/16 (hiring) | Closed N/A per P-INIT-5 | Consistent with solo + 11 AI model | ✅ Consistent |
| OQ-17/18 (funding/burn) | Closed out-of-scope per Session-2026-05-15 | Project tracks only AI dev caps via `cost-budget.yaml` | ✅ Consistent |

**New OQs that should be opened from W0 deferred items:**

- **OQ-NEW-1 (DEFERRED: slug collision policy)** — HANDOFF.md mentions H-DEFER-1 slug-collision behaviour for workspace provisioning. Currently `_sanitize_slug` falls back to `'workspace'` on empty input and `provision_initial_workspace` is "idempotent on slug lookup" — but the contract for "two users register with `slug='workspace'`" is implicit. This is a product/UX question (offer user a numeric suffix? a UUID-derived suffix? prompt user?). **Recommendation: open OQ-34 Wave-1 product decision before any user-facing slug surfaces in Phase 00.7.**
- **OQ-NEW-2 (DEFERRED: `@pytest.mark.live` provider tests)** — marker declared, no tests use it. Phase 00.6 owns populating real-provider live tests; confirm OQ to track real DeepSeek/Yandex/GigaChat API key procurement timeline.

---

## 9. Vision-to-code traceability (3 spot-checks)

### Check 1 — "AI-команд" (universal team paradigm)
- PROJECT.md:3 "Облачная платформа AI-команд для СМБ" → ADR-016 (team-first UX, no free-form agent comms) → ADR-024 (`agents` bounded context with team_presets + agent_instances) → roadmap phase 00.5 → **code stub** in `contracts/agents/schema.sql` (read).
- **Verdict: PASS** — vision → ADR → contract scaffold → phase-spec → code (forthcoming W0.5).

### Check 2 — "Pixel Department"
- PROJECT.md (header) + STATUS.md:14 + ADR-021 (AI-generated pixel pipeline) + R-14 (pixel-art bottleneck) + R-23 (AI-generated assets copyright) + R-24 (visual consistency) → roadmap Wave-2 anchor → no W0 code (correct).
- **Verdict: PASS** — vision → ADR + 3 risks → Wave-2 phase → deferred code per spec.

### Check 3 — "Master-Agent vertical-templates"
- PROJECT.md:9 + STATUS.md:11 + ADR-029 (Master-Agent layer) + R-32 (Master-Agent cost overhead) + ADR-017 revision (5 verticals + horizontal) → roadmap Wave-1 anchor (Marketing + Telegram-крейтор) → `cells.vertical_template_slug` reserved → no W0 code (correct).
- **Verdict: PASS** — vision → ADR + risk → Wave-1 phase → schema seam reserved → deferred code per spec.

**No orphan vision elements found.** Every PROJECT.md statement maps to an ADR + risk + phase + code/stub.

---

## 10. Target-date feasibility — 2026-06-09 (Wave-0 complete) + 2026-07-21 (Wave-1 complete)

### Velocity to date

| Phase | Calendar duration | Code volume (proxy) |
|---|---|---|
| 00.1 (repo+CI) | 1 day (2026-05-17, 2 days ahead of plan) | 8 atomic commits in PR #25 |
| Architect-PR | same day | iam contracts ext + Alembic bootstrap |
| 00.2 (auth) | 1 day (2026-05-18) | 14 atomic commits in PR #28, 86.69% iam coverage |
| 00.3 + 00.4 (combined) | 1 day (2026-05-19, parallel + combined PR) | 8 atomic + 9 follow-up CI/test commits, PR #30 |
| 00.2.5 (integration) | same day (2026-05-19 second pass) | 6 atomic commits + 5-agent audit + 366 unit + 21 integration tests |

**Average: ~1 calendar day per phase landed.** Wave-0 has 7 phases planned; 4 phases + integration done in 3 days. Remaining: 00.5 (5-day spec) + 00.6 (3-day spec) + 00.7 (4-day spec, parallel with 00.6).

### Remaining-work calendar (today → 2026-06-09)

- **Today: 2026-05-19** (Wave-0 60% by phase count, 50% by complexity)
- **Days remaining: 21 calendar days** to 2026-06-09
- **Work remaining: 12 person-days** (5 + 3 + 4) spec'd, but 00.5 has 19 enumerated tasks (phase-spec lines 374-394) which is the heaviest single phase of W0
- **Parallelism:** 00.6 ∥ 00.7 allowed per PHASES.md:24

### Feasibility rating: **TIGHT but achievable — confidence ~65%**

**Tailwinds:**
- Demonstrated daily-phase cadence (5 phases in 3 days).
- Phase 00.5 has a detailed phase-spec (467 lines, code skeletons, AC enumerated).
- Phase 00.6 ∥ 00.7 unlocks parallel close-out.
- Founder cost-budget allows running multiple Opus sessions concurrently.

**Headwinds:**
- Phase 00.5 is genuinely larger than any prior phase (Pydantic-AI runtime + 4 agents + tools + tasks + agents contexts + role-prompts + SSE + cost rollup + demo runner).
- Phase 00.6 introduces Yandex Cloud deploy + KMS swap + live LLM keys — first time touching production-class infra. Past phases were all local dev. High variance.
- 5-agent audit cycle per PR adds ~half-day per merge.
- Wave-0 acceptance gate requires the **demo to actually pass** (3 artefacts meet contracts, p95 ≤ 120s, cost ≤ 30¢). If first run misses the artefact-shape contract, iteration is needed.

**Recommendation:** Treat 2026-06-09 as 50/50. Founder should write an explicit "what we'd cut if we miss" list before Phase 00.5 starts — candidates: AC14 (role-prompt hardening backlog can move to 01.1 retro, already planned); demo cost cap relaxed from 30¢ to 50¢ if the cap is brushing (acceptable per ADR-031-style rationale); frontend skeleton (00.7) deferred to Wave-1 start as a soft slip if 00.5 is hot.

### Wave-1 (2026-07-21) feasibility

Wave-1 adds: horizontal hardening + 2 vertical templates (Marketing-agency + Telegram-крейтор) + Master-Agent first instances + Telegram Business API + memory + billing wiring + RBAC enforcement + 10-15 friends activation. 6-week target.

**Confidence: ~55%** — depends entirely on whether Wave-0 actually closes by 2026-06-09. If W0 slips to ~2026-06-16 (one-week slip), Wave-1 is still hittable (5-week run); if W0 slips two weeks, Wave-1 anchor should be re-evaluated.

---

## 11. Founder workflow ergonomics

### PR review burden
- PR #30 (00.3+00.4): 8 atomic + 9 follow-up CI/test = 17 commits in one PR.
- PR #32 (00.2.5): 7 atomic commits.
- **Verdict: HIGH but sustainable.** Atomic-commit discipline is keeping reviews tractable. Combined-PR pattern (00.3+00.4 → one PR) saved one full audit cycle but at the cost of bigger blast radius.

### Audit cycle
- 5-agent swarm per PR + cross-phase audits like this one + post-merge consistency audits.
- **Verdict: HIGH cost, HIGH value.** The audit caught 4 HIGH findings in 00.3+00.4 that would have shipped to main otherwise. Worth the spend.

### Worktree management
- 1 worktree per phase pattern (e.g. `claude/heuristic-rhodes-f7a3ef` for 00.2.5).
- **Verdict: STABLE.** Branch-naming + worktree-cleanup pattern is consistent across phases.

**No ergonomic red flags.** Pattern is stable. The only watch-item is **bus-factor on the founder** — a 4-week non-availability (illness, etc.) would freeze the whole pipeline since founder is the sole human reviewer. R-09 (founder burnout) is registered with mitigation "bus-week practice"; consider scheduling one before Wave-1 starts.

---

## 12. Wave-0 → Wave-1 transition readiness checklist

Per `gates/wave-0-to-1.md` (referenced in PHASES.md:54), the hard threshold is `internal_demo.passed=true`. Soft items below are the readiness inventory.

### Must-be-true before Phase 01.1 opens

| Item | Current state | Phase that closes it |
|---|---|---|
| All 7 Wave-0 phases ✅ Done | 4 ✅ + 1 (00.2.5) ✅ + 00.5/00.6/00.7 pending | 00.5 + 00.6 + 00.7 |
| Internal demo passes (Market & content brief) | ❌ Demo runner not yet built | 00.5 |
| 3 demo artefacts meet contracts (brief ≥1500w, matrix ≥5×4, plan = 10 posts) | ❌ Awaiting demo run | 00.5 |
| Demo p95 ≤ 120s + cost ≤ 30¢ | ❌ Awaiting demo run | 00.5 |
| Retro conducted | ❌ | Phase 00.7 close-out |
| Role-prompts hardening backlog populated (for 01.1) | ❌ Awaiting demo run failures | 00.5 AC14 |
| Risks register reviewed and updated | ⚠️ Partial — R-32, R-33, R-34 already opened mid-Wave-0; review pass deferred to 00.5 close-out | 00.5/00.7 close-out |
| Wave-1 README revised | ⚠️ Pre-W1 plan exists; concrete phase-specs JIT-generated per roadmap/README.md:60 | Wave-1 kickoff |
| Live LLM provider keys procured (DeepSeek + Yandex + GigaChat) | ❌ Placeholders only | 00.6 |
| Yandex KMS key provisioned | ❌ Placeholder | 00.6 |
| Deploy pipeline (staging) live | ❌ | 00.6 |
| Observability (Sentry + Langfuse + Yandex Monitoring) wired | ❌ Placeholders | 00.6 |
| Frontend skeleton against backend (TanStack Router + auth flow + cell list) | ❌ | 00.7 |
| OQ-04 closed (РКН confirmation) | Submitted, awaiting | Pre-prod, not pre-W1 launch |
| OQ-02 (ООО vs ИП) resolved | Open | Pre-Wave-1 ЮKassa opening (not pre-01.1 start) |
| OQ-19 (ЮKassa opening) | Open | Pre-Wave-1 billing |
| OQ-22 (friends list ≥30) + OQ-31 (positioning) | Open | Pre-Wave-1 launch |

### Recommended additions to the gate (not in current `gates/wave-0-to-1.md`)

1. **`accounting_ip` data-shape extensibility confirmed** — verify Phase 00.5 does not commit any per-cell schema that would constrain ИП-Бух (W3) data shape. Confirm `cells.settings_jsonb` remains the only per-vertical extension point.
2. **BYOK 9-provider coverage path documented** — confirm BYOK CRUD tolerates all 9 providers from ADR-008:56 OR document explicit deferral per provider.
3. **Master-Agent role-prompts directory scaffold (optional)** — Phase 00.5 can land an empty `contracts/role-prompts/masters/` with a single README "Wave-1+ destination" to lock in the structure.

---

## Findings — categorized by severity + in-loop vs. structural

### IN-LOOP — close during Phase 00.5

| # | Severity | Finding | Action |
|---|---|---|---|
| F-1 | Medium | `_BYOK_BASE_URLS` covers only OpenAI + Anthropic; ADR-008 tariff matrix promises 9 providers | Phase 00.5 verifies `byok_service.create_key(provider=...)` path tolerates DeepSeek/Yandex/GigaChat as BYOK upstreams OR ADR-008 amendment documents the W1+ rollout |
| F-2 | Medium | `ROLE_TO_MODEL` collapse to 4 keys (coordinator/specialist/embedder/default) — ADR-018 specifies per-agent-role mapping | Phase 00.5 expands the map per ADR-018:51-63 once writer/researcher/analyst agents land |
| F-3 | Medium | Anchor demo HTTP-path is 501 today; `test_llm_chat_endpoint_is_not_yet_wired` is the placeholder | Phase 00.5 replaces it with register → chat → cost-ledger E2E |
| F-4 | Low | `accounting_ip` data shape has no current contract artefact; `cells.settings_jsonb` is the only seam | Phase 00.5 must not commit any per-cell schema that constrains W3 ИП-Бух; confirmed by audit if Phase 00.5 reviewer-architect signs off |
| F-5 | Low | Master-Agent role-prompts directory `contracts/role-prompts/masters/` does not yet exist | Optional: Phase 00.5 lands an empty scaffold + README for W1+ destination |

### IN-LOOP — close during Phase 00.6

| # | Severity | Finding | Action |
|---|---|---|---|
| F-6 | Medium | Live LLM provider tests (`@pytest.mark.live`) — marker declared, suite empty | Phase 00.6 populates real-provider tests once API keys land |
| F-7 | Low | Data residency placeholders (`YC_FOLDER_ID`, etc.) untested | Phase 00.6 deploys to ru-central-1 + verifies |
| F-8 | Low | Yandex KMS swap from LocalAESKMS | Phase 00.6 |

### STRUCTURAL — open new OQ / track in backlog

| # | Severity | Finding | Action |
|---|---|---|---|
| S-1 | Low | OQ-NEW (slug collision UX) — `provision_initial_workspace` idempotent-on-slug but two distinct users with same email-localpart not yet contracted | Open OQ-34 (product/UX decision) pre-Phase 00.7 frontend |
| S-2 | Low | Sanctioned ADR-024 violation (billing import) — process drift risk | ADR-024 amendment in W1 refactor cycle; outbox/port pattern Wave-1+ |
| S-3 | Low | Legacy `organization` term in 6+ contract files (comments only; code clean) | Docs PR Phase 00.6 close-out |

### NONE BLOCKING — verdict-confidence retainer

| # | Note |
|---|---|
| N-1 | Founder bus-factor (R-09) — schedule one bus-week before Wave-1 (post 2026-06-09) |
| N-2 | Combined-PR pattern (00.3+00.4) saved one audit cycle but doubled blast radius — consider whether 00.6+00.7 should be combined or stay separate (recommendation: keep separate; 00.7 has frontend code that benefits from isolated review) |

---

## Wave-0 → Wave-1 transition checklist (consolidated)

```
[ ] Phase 00.5 merged with internal demo passing all 14 AC
[ ] Phase 00.6 merged with staging deploy live + live LLM keys + Yandex KMS
[ ] Phase 00.7 merged with frontend skeleton + auth flow + cells UI
[ ] Demo recorded + shared with founder + retro doc landed
[ ] Role-prompt hardening backlog populated for 01.1
[ ] Risks register reviewed (R-32/R-33/R-34 status confirmed; R-NEW-1..3 added if relevant)
[ ] OQ-34 (slug collision UX) opened or closed
[ ] OQ-22 (friends list ≥30) + OQ-31 (positioning) drafted by founder
[ ] OQ-19 (ЮKassa) procedure initiated
[ ] gates/wave-0-to-1.md threshold `internal_demo.passed=true` validated
[ ] Wave-1 README revised with concrete Phase 01.1 scope (Marketing-agency + Telegram-крейтор as anchor)
[ ] Wave-1 budget reviewed in .claude/agents/_shared/cost-budget.yaml
```

---

## Final verdict

**FLAG — proceed with Phase 00.5 and close the 5 IN-LOOP items during execution.**

The product is on-vision. No early Wave-0 decision has shipped that locks out any Wave-1+ vertical, any Wave-2-4 capability (Pixel/Mini App/Stars), or any FZ-152 commitment. The remaining gap to the anchor demo is exactly what Phase 00.5 is scoped to deliver, and the demonstrated velocity (5 phases in 3 days) supports the 2026-06-09 target with ~65% confidence — tight but achievable.

The single product risk worth founder attention before Phase 00.5 starts: **write down what you'd cut if Phase 00.5 + 00.6 collide.** Strong candidates: relax cost cap from 30¢ → 50¢, defer AC14 (role-prompt hardening backlog) to 01.1 retro (already planned per AC14 text), or slip 00.7 frontend skeleton into Wave-1 kickoff. None of those compromise the anchor demo. They are the pre-mortem hedge.

Target-date feasibility: **TIGHT but achievable.** No structural blockers. Five small in-loop closes during Phase 00.5 + three placeholder swaps in Phase 00.6 + zero scope-creep risk identified.

The founder can confidently open Phase 00.5 the moment PR #32 (00.2.5) lands on main.
