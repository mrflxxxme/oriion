# ADR-035: DeepSeek-gated native web_search tool-call (Researcher)

- **Status:** Accepted (Phase 01.1, 2026-06-17). The Settings `mock_mode` bug fix
  landed in the infra-PR; the native DeepSeek-gated tool-call landed in the focused
  follow-up (PRs [#45](https://github.com/mrflxxxme/oriion/pull/45) gateway tool-loop
  + [#46](https://github.com/mrflxxxme/oriion/pull/46) Researcher wiring). See
  **Update — Implemented** below.

## Context

AC-W1-19 asks for `web_search` to run as a **native Pydantic-AI tool-call** the
Researcher invokes autonomously, replacing the Wave-0 scripted runtime→mcp pre-fetch
(`fetch_research_context`). [ADR-032](./ADR-032-coordinator-plan-then-execute.md)
deliberately avoided native tool-calling for the Coordinator (the
`LLMGatewayModel` adapter has **no tool-loop at all**) and noted it "returns
pointwise for leaf web_search (AC-W1-19)" — i.e. exactly this decision.

During the infra-PR we confirmed the gateway adapter has zero tool plumbing: a real
implementation must thread Pydantic-AI function tools through
`LLMGatewayModel.request()` → `router_service.acomplete` → providers, parse
`tool_calls` into `ToolCallPart`s, and run the request/response tool-loop. That is
effectively its own feature and was split out of this PR (founder decision).

## Decision (for the follow-up)

1. **Landed now (bug fix):** `WebSearchTool` read `WEB_SEARCH_MOCK_MODE` from
   `os.environ` directly, so the `.env` flag threaded via Settings was ignored on the
   dispatch path — the cause of the Track A live **Brave HTTP 422**. Add an explicit
   `mock_mode` constructor param (env read kept only as a `None` fallback) and have
   `_default_web_search_tool` pass `settings.web_search_mock_mode`. **Settings is now
   the source of truth on the dispatch path.**

2. **Deferred (native tool-call):** wire `web_search` as a native Researcher tool
   **gated to DeepSeek** (the only provider that forwards `tools` /
   parses `tool_calls`). On a YandexGPT / GigaChat failover, **fall back to the
   scripted `fetch_research_context` pre-fetch** so the failover chain stays robust
   (Yandex/GigaChat silently drop tools → a native loop would break there). Rate-limit
   the native path via the Redis `ToolRateLimiter`.

## Why DeepSeek-gated, not all-providers

Forcing native tool-calls on all three providers would break `web_search` whenever the
circuit fails over to Yandex/GigaChat (they don't forward tools) — a failover-
robustness regression. Gating preserves [ADR-002](./ADR-002-llm-gateway.md)'s
plain-text-everywhere failover while still giving DeepSeek (the funded primary) the
autonomous tool-call behaviour AC-W1-19 wants. Acceptance is therefore an **honest
partial**: the runtime→mcp edge is removed *for DeepSeek* and retained as failover.

## Consequences

- AC-W1-19 stays **PARTIAL** after this PR (bug fixed; native deferred). The retro
  records it as such.
- The follow-up touches `pydantic_ai_model.py`, `router_service.acomplete`,
  `providers/base.py` (LLMRequest/LLMResponse `tool_calls` round-trip — `deepseek._body`
  already forwards `req.tools`), the Researcher agent factory, and `runtime/dispatch.py`
  (the gated fallback). Provider scaffolding partially exists; the adapter tool-loop is
  the hard part.

## Update — Implemented (2026-06-17)

The deferred native path landed exactly as decided above. AC-W1-19 is now **CLOSED**
(no longer PARTIAL). What shipped:

- **Gateway tool-loop** (PR #45): `LLMGatewayModel.request()` translates Pydantic-AI
  `function_tools` → OpenAI `tools`, forwards via `router_service.acomplete(tools=…)`,
  and parses response `tool_calls` → `ToolCallPart`s; `_messages_to_openai_shape` echoes
  the assistant `tool_calls` + feeds `ToolReturnPart`/`RetryPromptPart` back as
  `role="tool"` messages (the full request/response loop). `LLMRequest.tools` /
  `LLMResponse.tool_calls` already round-tripped in `providers/base.py`, so the schema
  was unchanged.
- **DeepSeek gate** (PR #45): `provider_forwards_tools()` + `_NATIVE_TOOL_PROVIDERS={"deepseek"}`;
  `acomplete` forwards tools **only to DeepSeek** and drops them on YandexGPT/GigaChat
  failover. `LLMRouter.would_use_native_tools(role_key)` lets the leaf predict the active
  provider.
- **Researcher wiring** (PR #46): `web_search` registered as a native tool on the
  DeepSeek path (no scripted pre-fetch); on failover `runtime.dispatch` falls back to
  `fetch_research_context`. The native loop is rate-limited via the Redis
  `ToolRateLimiter`, wired through `queue/actor.run_task_dispatch` → `dispatch_task`
  (the async Dramatiq path from ADR-034 — the request handler no longer dispatches
  inline). The direct runtime→mcp edge is removed for DeepSeek, retained as failover.

Tests: tool-loop round-trip (`test_pydantic_ai_model_adapter.py`), provider-gating +
tool-drop-on-failover (`test_router_service.py`), native-path dispatch (`test_dispatch.py`).
`mypy --strict src` + full pytest green.

## Links

- [ADR-032](./ADR-032-coordinator-plan-then-execute.md) — why native tool-calling is
  pointwise (leaf web_search), not for the Coordinator.
- [ADR-024](./ADR-024-bounded-context-contracts.md) §3 Exception #3 — the scripted
  runtime→mcp pre-fetch this would replace for DeepSeek.
- Phase-spec: `../roadmap/wave-1-core-mvp/phases/01.1-retro.md` AC-W1-19.
