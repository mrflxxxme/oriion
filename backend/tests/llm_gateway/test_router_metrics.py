"""AC-W1-13: LLMRouter.acomplete emits the 4 per-callsite LLM metrics.

Asserts deltas (the Prometheus counters are process-global + monotonic across the
session) so the test is robust to other tests touching the same label sets.
"""

from __future__ import annotations

from uuid import uuid4

import httpx
import pytest
from prometheus_client import REGISTRY
from src.llm_gateway.circuit_breaker import ProviderCircuit
from src.llm_gateway.providers.base import LLMRequest, LLMResponse, LLMUsage
from src.llm_gateway.services.router_service import LLMRouter


class _FakeProvider:
    def __init__(
        self,
        name: str,
        *,
        response: LLMResponse | None = None,
        exc: Exception | None = None,
    ) -> None:
        self.name = name
        self._response = response
        self._exc = exc

    async def chat(self, req: LLMRequest) -> LLMResponse:  # noqa: ARG002
        if self._exc is not None:
            raise self._exc
        assert self._response is not None
        return self._response


def _sample(name: str, labels: dict[str, str]) -> float:
    return REGISTRY.get_sample_value(name, labels) or 0.0


@pytest.mark.asyncio
async def test_acomplete_success_increments_request_tokens_latency() -> None:
    resp = LLMResponse(content="ok", usage=LLMUsage(tokens_input=11, tokens_output=22))
    providers = {"deepseek": _FakeProvider("deepseek", response=resp)}
    circuits = {"deepseek": ProviderCircuit(provider="deepseek")}
    router = LLMRouter(providers=providers, circuits=circuits)  # type: ignore[arg-type]

    req_labels = {"provider": "deepseek", "model": "deepseek-chat", "status": "success"}
    tok_labels = {"provider": "deepseek", "model": "deepseek-chat"}
    before_req = _sample("llm_request_total", req_labels)
    before_in = _sample("llm_tokens_input_total", tok_labels)
    before_out = _sample("llm_tokens_output_total", tok_labels)
    before_lat = _sample("llm_request_latency_seconds_count", tok_labels)

    _, model, slug = await router.acomplete(
        workspace_id=uuid4(),
        role_key="writer",  # → default → deepseek/deepseek-chat
        model_hint=None,
        messages=[{"role": "user", "content": "x"}],
    )

    assert (slug, model) == ("deepseek", "deepseek-chat")
    assert _sample("llm_request_total", req_labels) == before_req + 1
    assert _sample("llm_tokens_input_total", tok_labels) == before_in + 11
    assert _sample("llm_tokens_output_total", tok_labels) == before_out + 22
    assert _sample("llm_request_latency_seconds_count", tok_labels) == before_lat + 1


@pytest.mark.asyncio
async def test_acomplete_failover_records_error_then_success() -> None:
    ok_resp = LLMResponse(content="ok", usage=LLMUsage(tokens_input=5, tokens_output=7))
    providers = {
        "deepseek": _FakeProvider("deepseek", exc=httpx.ConnectError("boom")),
        "yandexgpt": _FakeProvider("yandexgpt", response=ok_resp),
    }
    circuits = {
        "deepseek": ProviderCircuit(provider="deepseek"),
        "yandexgpt": ProviderCircuit(provider="yandexgpt"),
    }
    router = LLMRouter(providers=providers, circuits=circuits)  # type: ignore[arg-type]

    err_labels = {"provider": "deepseek", "model": "deepseek-chat", "status": "error"}
    ok_labels = {"provider": "yandexgpt", "model": "yandexgpt/rc", "status": "success"}
    before_err = _sample("llm_request_total", err_labels)
    before_ok = _sample("llm_request_total", ok_labels)

    _, model, slug = await router.acomplete(
        workspace_id=uuid4(),
        role_key="writer",
        model_hint=None,
        messages=[{"role": "user", "content": "x"}],
    )

    assert slug == "yandexgpt"
    assert model.startswith("yandexgpt")
    # The failed primary recorded an error; the successful failover a success.
    assert _sample("llm_request_total", err_labels) == before_err + 1
    assert _sample("llm_request_total", ok_labels) == before_ok + 1
