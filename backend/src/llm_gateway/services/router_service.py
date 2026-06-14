"""LLMRouter — provider selection + failover chain.

Decision flow (per phase-spec 00.4):
    1. If `model_hint` is a BYOK spec (``byok-<provider>/<model>``) → BYOK proxy.
    2. Map `role_key` → default provider+model via ROLE_TO_MODEL.
    3. If circuit OPEN for primary → walk `failover_chain` until a CLOSED
       (or HALF_OPEN) circuit is found.
    4. If `model_hint` is set, override the model name but keep provider.

Wave 0 ROLE_TO_MODEL covers the agent archetypes mentioned in ADR-018.
"""

from __future__ import annotations

from uuid import UUID

import httpx
import structlog

from src.llm_gateway.circuit_breaker import CircuitState, ProviderCircuit
from src.llm_gateway.exceptions import LLMProviderUnavailable
from src.llm_gateway.providers.base import LLMProvider, LLMRequest, LLMResponse
from src.llm_gateway.providers.byok_proxy import parse_byok_model

logger = structlog.get_logger(__name__)

# ── ROLE_TO_MODEL — per ADR-018 ───────────────────────────────────────────
ROLE_TO_MODEL: dict[str, tuple[str, str]] = {
    # AC-W1-16b: Coordinator runs plan-then-execute via PromptedOutput (JSON).
    # deepseek-reasoner (R1) does NOT support JSON/function-calling and emits
    # reasoning prose in `content` (breaks the fenced-JSON parse) — so the
    # Coordinator uses deepseek-chat, which reliably follows the fence directive
    # and is cheaper/faster against the AC8/AC10 gates.
    "coordinator": ("deepseek", "deepseek-chat"),
    "specialist": ("deepseek", "deepseek-chat"),
    "embedder": ("yandexgpt", "text-search-doc"),
    "default": ("deepseek", "deepseek-chat"),
}

# ── Per-vertical failover order — first available wins ────────────────────
# Order chosen per phase-spec AC7: DeepSeek → YandexGPT → GigaChat.
_CHAT_CHAIN: tuple[str, ...] = ("deepseek", "yandexgpt", "gigachat")


class LLMRouter:
    """Stateless router over an immutable providers dict + mutable circuits.

    Providers + circuits are constructed at app startup and held by the FastAPI
    DI container; the router is instantiated per-request.
    """

    def __init__(
        self,
        *,
        providers: dict[str, LLMProvider],
        circuits: dict[str, ProviderCircuit],
    ) -> None:
        self._providers = providers
        self._circuits = circuits

    # -- public API -----------------------------------------------------------
    async def route(
        self,
        *,
        workspace_id: UUID,  # noqa: ARG002 — kept for cell-aware Wave 1+ routing
        role_key: str,
        model_hint: str | None,
    ) -> tuple[LLMProvider, str]:
        """Return ``(provider_instance, model_name)`` per the decision flow."""
        # 1) BYOK override (model_hint encodes provider).
        if model_hint and model_hint.startswith("byok-"):
            # BYOK keys are resolved by the router's caller (service layer
            # needs the workspace_id + KMS to construct the proxy) — here we
            # only validate the spec is parseable. The caller substitutes a
            # BYOKProxyProvider into the providers dict before calling chat().
            upstream_provider, upstream_model = parse_byok_model(model_hint)
            byok_key = f"byok-{upstream_provider}"
            if byok_key not in self._providers:
                raise LLMProviderUnavailable(
                    f"BYOK provider {byok_key!r} not registered (caller must "
                    "construct BYOKProxyProvider per-request)."
                )
            return self._providers[byok_key], upstream_model

        # 2) Role → default mapping.
        default_provider, default_model = ROLE_TO_MODEL.get(role_key, ROLE_TO_MODEL["default"])
        target_model = model_hint or default_model

        # 3) Walk the failover chain starting at default_provider.
        chain = self._chain_starting_at(default_provider)
        for slug in chain:
            provider = self._providers.get(slug)
            circuit = self._circuits.get(slug)
            if provider is None or circuit is None:
                continue
            if circuit.should_attempt:
                # If we switched to a non-primary, the upstream model name MUST
                # be re-mapped to that provider's catalog. If the original hint
                # is provider-specific (e.g. 'deepseek-chat' on yandex) we fall
                # back to that provider's default model.
                if slug != default_provider:
                    return provider, _provider_default_model(slug)
                return provider, target_model

        # 4) All providers down — raise.
        raise LLMProviderUnavailable(f"All providers in chain {chain!r} have OPEN circuits.")

    async def failover_chain(
        self,
        *,
        role_key: str,
        exclude: list[str],
    ) -> LLMProvider:
        """Return the next available provider, skipping `exclude` and OPEN circuits."""
        primary, _ = ROLE_TO_MODEL.get(role_key, ROLE_TO_MODEL["default"])
        chain = self._chain_starting_at(primary)
        for slug in chain:
            if slug in exclude:
                continue
            circuit = self._circuits.get(slug)
            provider = self._providers.get(slug)
            if circuit is None or provider is None:
                continue
            if circuit.state is CircuitState.OPEN and not circuit.try_half_open():
                continue
            return provider
        raise LLMProviderUnavailable(
            f"No fallback available (excluded={exclude!r}, chain={chain!r})."
        )

    async def acomplete(
        self,
        *,
        workspace_id: UUID,
        role_key: str,
        model_hint: str | None,
        messages: list[dict[str, str]],
        metadata: dict[str, str] | None = None,
    ) -> tuple[LLMResponse, str, str]:
        """Run a completion, failing over across the chain on retryable errors.

        Walks DeepSeek → YandexGPT → GigaChat (reordered to the role's primary):
        on any provider HTTP/network error (e.g. 402 Payment Required, 429, 5xx,
        connection error) it records the circuit failure and tries the NEXT
        provider — instead of the previous behaviour where a single provider
        error bubbled up and failed the whole task. Returns ``(response, model)``.

        BYOK requests (``byok-*`` hint) stay single-provider (per-workspace key,
        no cross-provider fallback).
        """
        if model_hint and model_hint.startswith("byok-"):
            provider, model = await self.route(
                workspace_id=workspace_id, role_key=role_key, model_hint=model_hint
            )
            resp = await provider.chat(
                LLMRequest(messages=messages, model=model, stream=False, metadata=metadata or {})
            )
            return resp, model, provider.name

        default_provider, default_model = ROLE_TO_MODEL.get(role_key, ROLE_TO_MODEL["default"])
        chain = self._chain_starting_at(default_provider)
        last_exc: Exception | None = None
        tried: list[str] = []
        for slug in chain:
            candidate = self._providers.get(slug)
            circuit = self._circuits.get(slug)
            if candidate is None or circuit is None or not circuit.should_attempt:
                continue
            if slug == default_provider:
                model = model_hint or default_model
            else:
                model = _provider_default_model(slug)
            try:
                resp = await candidate.chat(
                    LLMRequest(
                        messages=messages, model=model, stream=False, metadata=metadata or {}
                    )
                )
                circuit.record_success()
                return resp, model, slug
            except (httpx.HTTPError, LLMProviderUnavailable) as exc:
                circuit.record_failure()
                last_exc = exc
                tried.append(slug)
                logger.warning(
                    "llm_gateway.router.failover",
                    failed_provider=slug,
                    error=str(exc),
                    next_candidates=[s for s in chain if s not in tried],
                )
                continue
        if last_exc is not None:
            raise last_exc
        raise LLMProviderUnavailable(
            f"All providers in chain {chain!r} unavailable (none had a CLOSED circuit)."
        )

    # -- internals ------------------------------------------------------------
    @staticmethod
    def _chain_starting_at(primary: str) -> tuple[str, ...]:
        """Return _CHAT_CHAIN reordered so `primary` comes first."""
        if primary not in _CHAT_CHAIN:
            return (primary, *_CHAT_CHAIN)
        idx = _CHAT_CHAIN.index(primary)
        return _CHAT_CHAIN[idx:] + _CHAT_CHAIN[:idx]


def _provider_default_model(provider_slug: str) -> str:
    """Hardcoded default per provider (mirrors the 0001 migration seed).

    yandexgpt defaults to ``yandexgpt/rc`` = **YandexGPT 5.1 Pro** (modelVersion
    yagpt-5.1-2025-08) — the best Yandex model available in the founder's catalog
    (probed live 2026-06-07; the stable ``yandexgpt`` alias is 5.0 Pro). The
    YandexGPTProvider builds the modelUri verbatim when the name carries a
    version segment ("/"), so this resolves to gpt://<folder>/yandexgpt/rc.
    Falls back to the stable 5.0 Pro by setting model_hint="yandexgpt".
    """
    return {
        "deepseek": "deepseek-chat",
        "yandexgpt": "yandexgpt/rc",
        "gigachat": "GigaChat-Pro",
        "openai": "gpt-4o",
        "anthropic": "claude-sonnet-4-6",
    }.get(provider_slug, "default")
