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

from src.llm_gateway.circuit_breaker import CircuitState, ProviderCircuit
from src.llm_gateway.exceptions import LLMProviderUnavailable
from src.llm_gateway.providers.base import LLMProvider
from src.llm_gateway.providers.byok_proxy import parse_byok_model

# ── ROLE_TO_MODEL — per ADR-018 ───────────────────────────────────────────
ROLE_TO_MODEL: dict[str, tuple[str, str]] = {
    "coordinator": ("deepseek", "deepseek-reasoner"),
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

    # -- internals ------------------------------------------------------------
    @staticmethod
    def _chain_starting_at(primary: str) -> tuple[str, ...]:
        """Return _CHAT_CHAIN reordered so `primary` comes first."""
        if primary not in _CHAT_CHAIN:
            return (primary, *_CHAT_CHAIN)
        idx = _CHAT_CHAIN.index(primary)
        return _CHAT_CHAIN[idx:] + _CHAT_CHAIN[:idx]


def _provider_default_model(provider_slug: str) -> str:
    """Hardcoded default per provider (mirrors the 0001 migration seed)."""
    return {
        "deepseek": "deepseek-chat",
        "yandexgpt": "yandexgpt-pro",
        "gigachat": "GigaChat-Pro",
        "openai": "gpt-4o",
        "anthropic": "claude-sonnet-4-6",
    }.get(provider_slug, "default")
