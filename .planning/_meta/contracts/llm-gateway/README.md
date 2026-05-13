# Bounded context: `llm-gateway`

**Status:** DRAFT-READY (Milestone B.2, Wave 0)
**Owner:** backend-implementer + reviewer-security
**ADR refs:** [ADR-024](../../../decisions/ADR-024-bounded-context-contracts.md), [ADR-023](../../../decisions/ADR-023-ai-team-runtime.md)
**GRILL refs:** DECISION-7, **P-AUDIT-1** (cost-policy split)

## Purpose

Single gateway for **all** LLM calls inside Oriion. Unifies:

- **Provider routing** — DeepSeek, YandexGPT, GigaChat, Anthropic, OpenAI behind one OpenAI-shaped API.
- **BYOK custody** — per-organization keys encrypted with AES-256-GCM, never echoed.
- **Usage telemetry** — every call logged synchronously (tokens, latency, cost, status) for cost attribution and observability.
- **Failover** — when a provider degrades (>5% error rate / 5min) emit `provider.degraded.v1` and route to alternative provider within the same vertical capability.

## Ubiquitous language

| Term | Meaning |
|---|---|
| **Provider** | An upstream LLM vendor (`llm_provider_config` row). |
| **BYOKKey** | A per-organization customer-provided API key, AES-256-GCM-encrypted. |
| **PlatformKey** | An Oriion-managed key pool (not stored in `byok_keys`; referenced by `byok_key_id IS NULL` in usage log). |
| **UsageRecord** | One row in `llm_usage_log`; immutable. |

## Invariants

1. **No plaintext keys.** `raw_api_key` is never stored. Only AES-256-GCM ciphertext with per-organization KMS-wrapped DEK lives in `byok_keys.key_encrypted`.
2. **Synchronous logging.** Every LLM call writes a `llm_usage_log` row **before** the response is returned to the caller. No fire-and-forget.
3. **Cost-policy lives elsewhere.** This context tracks usage; it does **not** define policy. Per-role caps, Sonnet fallback rules, and the global kill-switch live in `.claude/agents/_shared/cost-budget.yaml` (**P-AUDIT-1**). The DDL `numeric(x,y)` columns are technical accounting, not budget thresholds. Comments in `schema.sql` make this explicit.
4. **BYOK soft-quota.** `byok_keys.monthly_quota_usd` is a **best-effort soft limit** — exceeding it emits `quota_exceeded.v1` but does **not** fail-closed (resilience over strict enforcement). The hard cap is the platform-wide cost-budget kill-switch (consumed via `oriion.billing.kill_switch.engaged.v1`).
5. **Auto-failover.** When `error_rate_pct > 5` over a rolling 5-minute window per `(provider_slug, model_name)`, emit `provider.degraded.v1` and route subsequent calls to the configured alternative within the same vertical capability (chat / embeddings / etc.).
6. **Fingerprint visibility.** Only `key_fingerprint` (sha256 of raw key, first 8 chars) is ever surfaced in API responses — never the ciphertext, never the raw key.

## External dependencies (cross-context)

| Context | Reason |
|---|---|
| `multitenancy` | `organization_id`, `cell_id` foreign keys; RLS settings sourced from `app.current_organization_id`. |
| `rbac` | Only `owner` / `admin` / `billing` system roles may CRUD `byok_keys` (enforced both in RLS and service layer). |
| `tasks` | `llm_usage_log.task_id` enables per-task cost attribution. |
| `agents` | Archetype `model_provider_slug` + `model_name` resolve to provider routing decisions. |
| `billing` | Consumes `request.completed.v1` for credit accounting; emits `kill_switch.engaged.v1`. |

## Out of scope

- Cost-policy enforcement logic (lives in `cost-budget.yaml` + billing context).
- Prompt content storage (lives in `_meta/verticals/<slug>/prompts/`).
- Agent orchestration (lives in `agents` and `tasks` contexts).

## Files

- [`schema.sql`](./schema.sql) — PostgreSQL 16 DDL with RLS policies.
- [`api.yaml`](./api.yaml) — OpenAPI 3.1.
- [`events.yaml`](./events.yaml) — CloudEvents 1.0 emit/consume contracts.
