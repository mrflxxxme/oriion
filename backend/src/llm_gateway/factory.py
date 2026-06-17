"""LLM provider-matrix + LLMRouter assembly — one source of truth.

Both the FastAPI lifespan (``src.main``) and the out-of-process Dramatiq
dispatch worker (``src.runtime.queue.worker``) need an identical LLMRouter
(DeepSeek primary → YandexGPT → GigaChat failover, per-provider httpx timeout,
per-provider circuit breakers). Phase 01.1 infra-PR (AC-W1-16a) extracts the
construction here so the web and worker processes can never drift.

Behaviour is identical to the pre-extraction lifespan block; the GigaChat TLS
seam (``gigachat_ca_bundle`` / ``gigachat_verify_ssl``, AC-W1-21) is read from
Settings so the worker honours the same in-container CA configuration.
"""

from __future__ import annotations

from typing import NamedTuple, cast

from src._shared.config import Settings
from src.llm_gateway.circuit_breaker import ProviderCircuit
from src.llm_gateway.providers.base import LLMProvider
from src.llm_gateway.providers.deepseek import DeepSeekProvider
from src.llm_gateway.providers.gigachat import GigaChatProvider
from src.llm_gateway.providers.yandex import YandexGPTProvider
from src.llm_gateway.services.router_service import LLMRouter


class LLMRouterBundle(NamedTuple):
    """The provider matrix + circuits + router, stashed on app.state by the
    web process and held locally by the worker process."""

    providers: dict[str, LLMProvider]
    circuits: dict[str, ProviderCircuit]
    router: LLMRouter


def build_llm_router(settings: Settings) -> LLMRouterBundle:
    """Construct the DeepSeek/YandexGPT/GigaChat matrix + circuits + LLMRouter.

    Providers are constructed with whatever credentials Settings holds. An empty
    credential just means calls to that provider's HTTP API fail at request-time
    — boot stays green so health probes (`/api/v1/llm/providers`) still answer.

    The provider classes implement the LLMProvider Protocol structurally (they
    don't inherit it); mypy --strict won't auto-narrow concrete -> Protocol in a
    dict-assignment context, so ``cast`` is the explicit Protocol-boundary
    acknowledgement (shape verified in tests/llm_gateway/test_provider_*_mock.py).
    """
    provider_timeout = settings.llm_provider_timeout_seconds
    # GigaChat TLS: prefer an explicit CA bundle (the prod image points this at
    # the system store that carries the Russian Trusted Root CA) over the bare
    # verify bool, because httpx/certifi ignores the OS cert store. AC-W1-21.
    gigachat_verify: bool | str = settings.gigachat_ca_bundle or settings.gigachat_verify_ssl

    providers: dict[str, LLMProvider] = {}
    providers["deepseek"] = cast(
        LLMProvider,
        DeepSeekProvider(
            api_key=settings.deepseek_api_key.get_secret_value(),
            timeout_seconds=provider_timeout,
        ),
    )
    providers["yandexgpt"] = cast(
        LLMProvider,
        YandexGPTProvider(
            catalog_id=settings.yandex_catalog_id,
            # Api-Key scheme preferred (non-expiring); IAM Bearer is the
            # legacy/failover credential. Empty IAM → None (treated as unset).
            api_key=settings.yandex_api_key,
            iam_token=settings.yandex_iam_token.get_secret_value() or None,
            timeout_seconds=provider_timeout,
        ),
    )
    providers["gigachat"] = cast(
        LLMProvider,
        GigaChatProvider(
            auth_key=settings.gigachat_auth_key.get_secret_value(),
            timeout_seconds=provider_timeout,
            verify_ssl=gigachat_verify,
        ),
    )
    circuits = {slug: ProviderCircuit(provider=slug) for slug in providers}
    router = LLMRouter(providers=providers, circuits=circuits)
    return LLMRouterBundle(providers=providers, circuits=circuits, router=router)
