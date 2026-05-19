"""Pydantic 2.x schemas for llm_gateway — matches contracts/llm-gateway/api.yaml 1:1.

All money fields use Decimal so JSON serialization rounds-trips without
silent float widening (per ADR-018 amendment, Wave 0 currency model).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# Capability literal used for `feature` filter on /llm/providers.
FeatureLiteral = Literal["chat", "embeddings", "structured_output", "tool_use", "vision"]
ProviderHealthLiteral = Literal["healthy", "degraded", "down"]
CircuitLiteral = Literal["closed", "open", "half_open"]
StatusLiteral = Literal["success", "error", "timeout", "rate_limited"]
RoleLiteral = Literal["system", "user", "assistant", "tool"]


# ── Providers ──────────────────────────────────────────────────────────────


class ProviderOut(BaseModel):
    """GET /llm/providers item."""

    model_config = ConfigDict(extra="ignore")

    provider_slug: str
    display_name: str
    default_model: str
    base_url: str
    is_byok_supported: bool
    supported_features: list[FeatureLiteral]


class ProviderStatusOut(BaseModel):
    """GET /llm/providers/status item."""

    provider_slug: str
    state: ProviderHealthLiteral
    circuit: CircuitLiteral
    last_check: datetime


# ── BYOK ───────────────────────────────────────────────────────────────────


class BYOKKeyCreateRequest(BaseModel):
    """POST /llm/byok-keys body.

    `raw_api_key` is write-only — never echoed in any response shape.
    """

    model_config = ConfigDict(extra="forbid")

    provider_slug: str
    raw_api_key: str = Field(min_length=8, repr=False)
    label: str = Field(min_length=1, max_length=80)
    monthly_quota_usd: Decimal | None = None


class BYOKKeyOut(BaseModel):
    """POST/GET /llm/byok-keys response item. NEVER contains plaintext."""

    model_config = ConfigDict(extra="ignore")

    id: UUID
    provider_slug: str
    key_fingerprint: str = Field(description="sha256(raw_key)[:8]")
    label: str
    monthly_quota_usd: Decimal | None = None
    monthly_used_usd: Decimal
    is_active: bool
    created_at: datetime
    revoked_at: datetime | None = None


# ── Chat / Inference ───────────────────────────────────────────────────────


class ChatMessage(BaseModel):
    """One message in a chat completion request."""

    model_config = ConfigDict(extra="forbid")
    role: RoleLiteral
    content: str


class ChatCompletionRequest(BaseModel):
    """POST /llm/chat/completions body.

    `model` may be `"byok-openai/gpt-4o"` to route through a BYOK proxy — the
    string before the slash is the provider_slug, after the slash is the
    upstream model name. See router_service.LLMRouter.route().
    """

    model_config = ConfigDict(extra="ignore")

    provider_slug: str | None = None
    model: str | None = None
    byok_key_id: UUID | None = None
    messages: list[ChatMessage] = Field(min_length=1)
    temperature: float | None = None
    max_tokens: int | None = None
    tools: list[dict[str, object]] | None = None
    stream: bool = False


class Usage(BaseModel):
    """Per-call usage block (chat completion + embedding shared shape)."""

    model_config = ConfigDict(extra="ignore")
    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0
    cost_usd: Decimal = Decimal(0)
    cost_rub: Decimal = Decimal(0)
    fx_rate_usd_to_rub: Decimal = Decimal(0)
    latency_ms: int = 0


class ChatChoiceMessage(BaseModel):
    role: str
    content: str


class ChatChoice(BaseModel):
    index: int
    message: ChatChoiceMessage
    finish_reason: str


class ChatCompletionResponse(BaseModel):
    """POST /llm/chat/completions response."""

    request_id: str
    provider_slug: str
    model: str
    choices: list[ChatChoice]
    usage: Usage


# ── Embeddings ─────────────────────────────────────────────────────────────


class EmbeddingRequest(BaseModel):
    """POST /llm/embeddings body."""

    model_config = ConfigDict(extra="ignore")
    provider_slug: str
    model: str
    input: str | list[str]


class EmbeddingItem(BaseModel):
    index: int
    embedding: list[float]


class EmbeddingResponse(BaseModel):
    request_id: str
    model: str
    data: list[EmbeddingItem]
    usage: Usage


# ── Usage ──────────────────────────────────────────────────────────────────


class UsageStatsRow(BaseModel):
    key: str
    total_input: int
    total_output: int
    total_cost_usd: Decimal
    total_cost_rub: Decimal
    call_count: int


class UsageStats(BaseModel):
    """GET /llm/usage response."""

    period_from: datetime = Field(serialization_alias="from")
    period_to: datetime = Field(serialization_alias="to")
    group_by: str
    rows: list[UsageStatsRow]


# ── Errors ─────────────────────────────────────────────────────────────────


class ErrorResponse(BaseModel):
    """Canonical error envelope (matches api.yaml Error component)."""

    code: str
    message: str
    details: dict[str, object] | None = None
