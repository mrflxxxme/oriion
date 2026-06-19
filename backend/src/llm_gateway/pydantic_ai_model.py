"""Pydantic-AI Model adapter wrapping LLMRouter.

Phase 00.5b Commit 4. Bridges the Pydantic-AI ``Agent(model=...)`` runtime
with the in-house ``LLMRouter`` (provider failover + BYOK + cost ledger).

Why a custom adapter (not pydantic_ai's OpenAIModel / GoogleModel / etc.):

* Our providers (DeepSeek + YandexGPT + GigaChat) have RU-specific quirks
  (Yandex modelUri, GigaChat OAuth on-demand refresh, GigaChat Sber TLS).
* The failover chain + circuit breakers + per-tenant BYOK proxying live
  inside ``LLMRouter`` — Pydantic-AI's per-provider classes would each
  need to redo the same plumbing.
* The cost-rollup + RU-currency triad (cost_usd + cost_rub + fx_rate) is
  owned by ``billing_service.record_llm_cost`` — wiring it through a
  generic OpenAI-shape model would require a second adapter layer.

Test path: ``tests/_fixtures/canned_pydantic_ai/fake_model.py`` ships a
``FakeLLMGatewayModel`` with identical interface that returns canned
``ModelResponse`` lists keyed by ``(role_key, scenario_id)`` — fail-loud
on unknown keys per founder-resolved T3 mock pattern. The fake is what
agent integration tests instantiate; the real adapter is exercised by
``test_pydantic_ai_model_adapter.py`` + by Phase 00.6 staging runs.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Literal, cast
from uuid import UUID

from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    ModelResponsePart,
    RetryPromptPart,
    SystemPromptPart,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models import Model
from pydantic_ai.usage import RequestUsage

from src.llm_gateway.services.router_service import resolve_max_tokens

# Pydantic-AI's ModelResponse.finish_reason is typed as a strict Literal.
_FinishReason = Literal["stop", "length", "content_filter", "tool_call", "error"]

if TYPE_CHECKING:
    from pydantic_ai.models import ModelRequestParameters
    from pydantic_ai.settings import ModelSettings
    from pydantic_ai.tools import ToolDefinition

    from src.llm_gateway.services.router_service import LLMRouter


_SYSTEM_TAG = "oriion-llm-gateway"


class LLMGatewayModel(Model):
    """Pydantic-AI Model implementation backed by ``LLMRouter``.

    Args:
        role_key: maps to ROLE_TO_MODEL in router_service.py — selects the
            primary provider/model pair (e.g. "coordinator" → deepseek/r1).
            Required so the router knows which chain to walk.
        llm_router: process-wide router instance (built in main.lifespan;
            injected via FastAPI DI in handlers, or passed directly in
            agent tests).
        workspace_id: cell-aware Wave-1+ routing hook. For Wave 0 a UUID
            placeholder is fine — the router currently ignores it.
        model_hint: optional override forwarded to ``LLMRouter.route(...)``.
            Use BYOK strings (``byok-<provider>/<model>``) to opt into
            per-workspace keys.
    """

    def __init__(
        self,
        role_key: str,
        llm_router: LLMRouter,
        *,
        workspace_id: UUID | None = None,
        model_hint: str | None = None,
    ) -> None:
        super().__init__()
        self._role_key = role_key
        self._router = llm_router
        self._workspace_id = workspace_id or UUID("00000000-0000-0000-0000-000000000000")
        self._model_hint = model_hint
        # Last provider/model actually selected by the failover chain — read by
        # the leaf runner to bill the call via record_llm_cost (AC-W1-13).
        self._last_model_name: str | None = None
        self._last_provider_slug: str | None = None

    # ── abstract Model interface ─────────────────────────────────────────

    @property
    def model_name(self) -> str:
        """Stable identifier surfaced in usage logs + audit trail."""
        return f"{_SYSTEM_TAG}/{self._role_key}"

    @property
    def system(self) -> str:
        return _SYSTEM_TAG

    async def request(
        self,
        messages: list[ModelRequest | ModelResponse],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
    ) -> ModelResponse:
        """One-shot completion. Streaming sibling lives in ``request_stream``
        (inherited default raises until Wave 1 SSE-on-runtime lands).

        ``prepare_request`` resolves the PromptedOutput schema instructions
        (AC-W1-16b): for a ``PromptedOutput``-configured Agent (the Coordinator)
        ``prompted_output_instructions`` is the JSON-schema directive, which we
        inject as a system message so the provider returns schema-conformant JSON
        — no function-calling required (works across DeepSeek/Yandex/GigaChat).
        Leaf agents (``output_type=str``) yield ``None`` here → unchanged path.

        Native tool-calling (AC-W1-19): an Agent built with function tools (the
        Researcher's ``web_search``) surfaces them as ``function_tools`` here. We
        translate them to the OpenAI ``tools`` shape and forward via ``acomplete``,
        which gates the forwarding to DeepSeek (ADR-035). Any ``tool_calls`` in the
        response are parsed back into ``ToolCallPart``s so Pydantic-AI runs the
        tool and re-enters ``request`` with the ``ToolReturnPart`` (the tool-loop).
        """
        _, model_request_parameters = self.prepare_request(model_settings, model_request_parameters)
        openai_messages = _messages_to_openai_shape(
            messages,
            prompted_instructions=model_request_parameters.prompted_output_instructions,
        )
        tools = _tool_defs_to_openai(model_request_parameters.function_tools)

        # acomplete walks the failover chain (DeepSeek → YandexGPT → GigaChat),
        # so a single provider error (e.g. 402 Payment Required) fails over to
        # the next provider instead of failing the whole task.
        resp, target_model, provider_slug = await self._router.acomplete(
            workspace_id=self._workspace_id,
            role_key=self._role_key,
            model_hint=self._model_hint,
            messages=openai_messages,
            metadata={"role_key": self._role_key, "workspace_id": str(self._workspace_id)},
            max_tokens=resolve_max_tokens(self._role_key),
            tools=tools,
        )
        self._last_model_name = target_model
        self._last_provider_slug = provider_slug

        parts: list[ModelResponsePart] = []
        if resp.content:
            parts.append(TextPart(content=resp.content))
        parts.extend(_tool_calls_to_parts(resp.tool_calls))
        if not parts:
            # An empty completion (no text, no tool calls) — keep parts non-empty
            # so the Pydantic-AI graph has a stable TextPart to consume.
            parts.append(TextPart(content=""))

        return ModelResponse(
            parts=parts,
            usage=RequestUsage(
                input_tokens=resp.usage.tokens_input,
                output_tokens=resp.usage.tokens_output,
                cache_read_tokens=resp.usage.cached_input_tokens,
                details={},
            ),
            model_name=f"{_SYSTEM_TAG}/{target_model}",
            timestamp=datetime.now(UTC),
            finish_reason=_normalize_finish_reason(resp.finish_reason),
            provider_name=provider_slug,
        )

    # F-ARC-M1 audit fix: request_stream() is intentionally NOT overridden in
    # Wave 0. Pydantic-AI's Model ABC provides a default that raises a clear
    # error when an Agent built with this model attempts run_stream(). Wave-1
    # hardening (AC14) wires the streaming bridge through
    # `runtime.sse_publisher.TaskStreamEvent('task.step_token')`.


# ── helpers ──────────────────────────────────────────────────────────────


def _messages_to_openai_shape(
    messages: list[ModelRequest | ModelResponse],
    *,
    prompted_instructions: str | None = None,
) -> list[dict[str, Any]]:
    """Translate Pydantic-AI ``ModelRequest``/``ModelResponse`` parts → OpenAI-shape.

    Handles the plan-then-execute text path (Coordinator ``PromptedOutput``) AND
    the native tool-loop (Researcher ``web_search``, AC-W1-19):

    * ``SystemPromptPart`` / ``UserPromptPart`` → system/user messages.
    * ``TextPart`` (assistant) → assistant message content.
    * ``ToolCallPart`` → an assistant message carrying the OpenAI ``tool_calls``
      array (so the next request echoes back the model's prior tool request).
    * ``ToolReturnPart`` / ``RetryPromptPart`` → ``role="tool"`` messages keyed by
      ``tool_call_id`` (the tool result the model needs to continue the loop).

    ``prompted_instructions`` (from ``ModelRequestParameters.prompted_output_instructions``)
    carries the PromptedOutput JSON-schema directive.

    **All system content is merged into a SINGLE system message** (role prompt
    first, then the schema directive). PromptedOutput would otherwise add a second
    system message, and some providers in the failover chain reject multiple system
    roles — a live GigaChat run returned 422 on the two-system-message Coordinator
    request (ADR-032 multi-system fallback). DeepSeek accepts either, so merging is
    strictly safer across DeepSeek / YandexGPT / GigaChat.
    """
    system_parts: list[str] = []
    rest: list[dict[str, Any]] = []
    for msg in messages:
        if isinstance(msg, ModelRequest):
            for req_part in msg.parts:
                if isinstance(req_part, SystemPromptPart):
                    system_parts.append(req_part.content)
                elif isinstance(req_part, UserPromptPart):
                    content = (
                        req_part.content
                        if isinstance(req_part.content, str)
                        else str(req_part.content)
                    )
                    rest.append({"role": "user", "content": content})
                elif isinstance(req_part, ToolReturnPart):
                    rest.append(
                        {
                            "role": "tool",
                            "tool_call_id": req_part.tool_call_id,
                            "content": req_part.model_response_str(),
                        }
                    )
                elif isinstance(req_part, RetryPromptPart):
                    # Tool-arg validation failure → feed the error back as the
                    # tool result so the model can correct its next tool call.
                    rest.append(
                        {
                            "role": "tool",
                            "tool_call_id": req_part.tool_call_id,
                            "content": req_part.model_response(),
                        }
                    )
        elif isinstance(msg, ModelResponse):
            text_chunks: list[str] = []
            tool_calls: list[dict[str, Any]] = []
            for resp_part in msg.parts:
                if isinstance(resp_part, TextPart):
                    text_chunks.append(resp_part.content)
                elif isinstance(resp_part, ToolCallPart):
                    tool_calls.append(
                        {
                            "id": resp_part.tool_call_id,
                            "type": "function",
                            "function": {
                                "name": resp_part.tool_name,
                                "arguments": resp_part.args_as_json_str(),
                            },
                        }
                    )
            assistant_msg: dict[str, Any] = {
                "role": "assistant",
                "content": "\n".join(text_chunks),
            }
            if tool_calls:
                assistant_msg["tool_calls"] = tool_calls
            rest.append(assistant_msg)

    # Schema directive goes after the role/system context.
    if prompted_instructions:
        system_parts.append(prompted_instructions)

    openai_messages: list[dict[str, Any]] = []
    if system_parts:
        openai_messages.append({"role": "system", "content": "\n\n".join(system_parts)})
    openai_messages.extend(rest)
    return openai_messages


def _tool_defs_to_openai(
    tool_defs: list[ToolDefinition],
) -> list[dict[str, Any]] | None:
    """Translate Pydantic-AI ``ToolDefinition``s → OpenAI ``tools`` array.

    Returns ``None`` when there are no tools so the provider body omits the key
    entirely (an empty ``tools: []`` confuses some OpenAI-compatible backends).
    """
    if not tool_defs:
        return None
    return [
        {
            "type": "function",
            "function": {
                "name": td.name,
                "description": td.description or "",
                "parameters": td.parameters_json_schema,
            },
        }
        for td in tool_defs
    ]


def _tool_calls_to_parts(
    tool_calls: list[dict[str, Any]] | None,
) -> list[ToolCallPart]:
    """Parse provider ``tool_calls`` (OpenAI shape) → Pydantic-AI ``ToolCallPart``s.

    DeepSeek returns ``{"id", "type": "function", "function": {"name", "arguments"}}``;
    ``arguments`` is a JSON string, which ``ToolCallPart`` accepts verbatim (it
    parses it when the tool runs).
    """
    parts: list[ToolCallPart] = []
    for call in tool_calls or []:
        fn = call.get("function") or {}
        name = fn.get("name")
        if not name:
            continue
        parts.append(
            ToolCallPart(
                tool_name=str(name),
                args=fn.get("arguments") or "{}",
                tool_call_id=str(call.get("id") or ""),
            )
        )
    return parts


_VALID_FINISH_REASONS: frozenset[str] = frozenset(
    {"stop", "length", "content_filter", "tool_call", "error"}
)


def _normalize_finish_reason(raw: str | None) -> _FinishReason | None:
    """Coerce provider-specific finish reasons to Pydantic-AI's vocabulary.

    Pydantic-AI uses {'stop', 'length', 'content_filter', 'tool_call', 'error'};
    DeepSeek + Yandex + GigaChat all return 'stop' / 'length' / 'tool_calls'
    in their happy path. Unknown values map to 'stop' (Wave-0 safe default).
    """
    if raw is None or raw == "stop":
        return "stop"
    # DeepSeek returns the plural 'tool_calls' when the turn ended on a native
    # tool request (AC-W1-19) — map to Pydantic-AI's singular 'tool_call'.
    if raw == "tool_calls":
        return "tool_call"
    if raw in _VALID_FINISH_REASONS:
        return cast(_FinishReason, raw)
    # Unknown / provider-specific tokens map to 'stop' so the Pydantic-AI Literal
    # contract holds.
    return "stop"
