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
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    TextPart,
    UserPromptPart,
)
from pydantic_ai.models import Model
from pydantic_ai.usage import RequestUsage

from src.llm_gateway.providers.base import LLMRequest

if TYPE_CHECKING:
    from pydantic_ai.models import ModelRequestParameters
    from pydantic_ai.settings import ModelSettings

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
        self._last_model_name: str | None = None

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
        model_settings: ModelSettings | None,  # noqa: ARG002 — reserved, Wave-1+
        model_request_parameters: ModelRequestParameters,  # noqa: ARG002 — tools/output_mode wire-up Wave 1
    ) -> ModelResponse:
        """One-shot completion. Streaming sibling lives in ``request_stream``
        (inherited default raises until Wave 1 SSE-on-runtime lands)."""
        openai_messages = _messages_to_openai_shape(messages)

        provider, target_model = await self._router.route(
            workspace_id=self._workspace_id,
            role_key=self._role_key,
            model_hint=self._model_hint,
        )
        self._last_model_name = target_model

        req = LLMRequest(
            messages=openai_messages,
            model=target_model,
            stream=False,
            metadata={"role_key": self._role_key, "workspace_id": str(self._workspace_id)},
        )
        resp = await provider.chat(req)

        return ModelResponse(
            parts=[TextPart(content=resp.content)],
            usage=RequestUsage(
                input_tokens=resp.usage.tokens_input,
                output_tokens=resp.usage.tokens_output,
                cache_read_tokens=resp.usage.cached_input_tokens,
                details={},
            ),
            model_name=f"{_SYSTEM_TAG}/{target_model}",
            timestamp=datetime.now(UTC),
            finish_reason=_normalize_finish_reason(resp.finish_reason),
            provider_name=provider.name,
        )

    async def request_stream(  # type: ignore[override]
        self,
        messages: list[ModelRequest | ModelResponse],  # noqa: ARG002
        model_settings: ModelSettings | None,  # noqa: ARG002
        model_request_parameters: ModelRequestParameters,  # noqa: ARG002
        run_context: object | None = None,  # noqa: ARG002
    ):
        """F-ARC-M1 audit fix: explicit loud NotImplementedError instead of
        relying on Pydantic-AI's inherited default. The streaming sibling
        wires up in Wave 1 once SSE-on-runtime hooks the per-token surface
        through `runtime.sse_publisher.TaskStreamEvent('task.step_token')`.
        """
        raise NotImplementedError(
            "LLMGatewayModel.request_stream is not implemented in Wave 0. "
            "Pydantic-AI Agent.run_stream() is not exercised by the "
            "productivity-core demo flow yet. Wave-1 hardening pass (AC14) "
            "lands the streaming bridge — see ADR-003 and "
            "phases/00.5-pydantic-ai-productivity-team.md notes."
        )
        yield  # pragma: no cover — for type-checker, never reached


# ── helpers ──────────────────────────────────────────────────────────────


def _messages_to_openai_shape(
    messages: list[ModelRequest | ModelResponse],
) -> list[dict[str, str]]:
    """Translate Pydantic-AI ``ModelRequest``/``ModelResponse`` parts → OpenAI-shape.

    Only Text-style parts are handled in Wave 0 (the productivity-core demo
    flow doesn't surface tool-calls or media yet). Tool-call wiring lands
    with Commit 5 when ``delegate_task`` ships.
    """
    openai_messages: list[dict[str, str]] = []
    for msg in messages:
        if isinstance(msg, ModelRequest):
            for part in msg.parts:
                if isinstance(part, SystemPromptPart):
                    openai_messages.append({"role": "system", "content": part.content})
                elif isinstance(part, UserPromptPart):
                    content = part.content if isinstance(part.content, str) else str(part.content)
                    openai_messages.append({"role": "user", "content": content})
        elif isinstance(msg, ModelResponse):
            for part in msg.parts:
                if isinstance(part, TextPart):
                    openai_messages.append({"role": "assistant", "content": part.content})
    return openai_messages


def _normalize_finish_reason(raw: str | None) -> str | None:
    """Coerce provider-specific finish reasons to Pydantic-AI's vocabulary.

    Pydantic-AI uses {'stop', 'length', 'content_filter', 'tool_call', 'error'};
    DeepSeek + Yandex + GigaChat all return 'stop' / 'length' / 'tool_calls'
    in their happy path. Unknown values pass through unchanged so we don't
    silently lose information.
    """
    if raw is None or raw == "stop":
        return "stop"
    return raw
