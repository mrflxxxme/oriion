"""Provider abstraction — LLMProvider Protocol + Request / Response / Usage models.

Per phase-spec 00.4 inline definition. Money fields use Decimal to keep
billing paths float-free per ADR-018.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from decimal import Decimal
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field


class LLMRequest(BaseModel):
    """OpenAI-shaped request passed into ``LLMProvider.chat()``.

    `metadata` carries gateway-side context (cell_id, task_id, role_key) used
    by the billing/audit layer — providers themselves SHOULD NOT forward
    arbitrary metadata to upstream APIs.
    """

    model_config = ConfigDict(extra="ignore")

    messages: list[dict[str, Any]] = Field(min_length=1)
    model: str
    max_tokens: int = 2048
    temperature: float = 0.7
    stream: bool = False
    tools: list[dict[str, Any]] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class LLMUsage(BaseModel):
    """Per-call usage data returned by a provider.

    Providers are responsible for returning `tokens_input` + `tokens_output`;
    cost columns are computed downstream by ``billing_service.record_llm_cost``
    using ``pricing_service.calculate_cost_usd_and_rub``. Providers MAY
    populate `cost_rub` directly if they know native pricing (RU providers
    bill in RUB) — billing service still reconciles via pricing table.
    """

    model_config = ConfigDict(extra="ignore")

    tokens_input: int = 0
    tokens_output: int = 0
    cached_input_tokens: int = 0
    cost_rub: Decimal = Decimal(0)


class LLMResponse(BaseModel):
    """Single chat-completion result (full response or one stream chunk)."""

    model_config = ConfigDict(extra="ignore")

    content: str
    finish_reason: str = "stop"
    tool_calls: list[dict[str, Any]] | None = None
    usage: LLMUsage = Field(default_factory=LLMUsage)
    raw_provider_metadata: dict[str, Any] = Field(default_factory=dict)


class LLMProvider(Protocol):
    """Interface for DeepSeek / YandexGPT / GigaChat / OpenAI / Anthropic providers.

    Implementations live under ``src.llm_gateway.providers``. The router holds
    one instance per provider_slug for the process lifetime.
    """

    name: str

    async def chat(self, req: LLMRequest) -> LLMResponse:
        """Non-streaming chat completion."""
        ...

    async def chat_stream(self, req: LLMRequest) -> AsyncIterator[LLMResponse]:
        """Streaming chat — yields incremental ``LLMResponse`` chunks."""
        ...

    async def embeddings(self, texts: list[str], model: str) -> list[list[float]]:
        """Generate embedding vectors. Raise NotImplementedError if unsupported."""
        ...

    async def health_check(self) -> bool:
        """Single ping used by health-monitor. Return True iff upstream reachable."""
        ...
