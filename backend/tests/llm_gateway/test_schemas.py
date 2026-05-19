"""Unit tests — Pydantic schemas conform to contracts/llm-gateway/api.yaml."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError
from src.llm_gateway.schemas import (
    BYOKKeyCreateRequest,
    BYOKKeyOut,
    ChatCompletionRequest,
    ChatMessage,
    EmbeddingRequest,
    ProviderOut,
    Usage,
)


def test_byok_create_request_requires_min_key_len() -> None:
    with pytest.raises(ValidationError):
        BYOKKeyCreateRequest(provider_slug="openai", raw_api_key="short", label="ok")


def test_byok_create_request_accepts_decimal_quota() -> None:
    req = BYOKKeyCreateRequest(
        provider_slug="openai",
        raw_api_key="sk-test-very-long-fake-key",  # gitleaks:allow
        label="Marketing OpenAI",
        monthly_quota_usd=Decimal("50.00"),
    )
    assert req.monthly_quota_usd == Decimal("50.00")


def test_byok_out_never_exposes_raw_key() -> None:
    out = BYOKKeyOut(
        id=uuid4(),
        provider_slug="openai",
        key_fingerprint="abcd1234",
        label="Marketing",
        monthly_quota_usd=None,
        monthly_used_usd=Decimal("0"),
        is_active=True,
        created_at=datetime.now(UTC),
    )
    payload = out.model_dump()
    assert "raw_api_key" not in payload
    assert "key_encrypted" not in payload


def test_chat_completion_request_requires_at_least_one_message() -> None:
    with pytest.raises(ValidationError):
        ChatCompletionRequest(messages=[])


def test_chat_completion_request_accepts_byok_model() -> None:
    req = ChatCompletionRequest(
        model="byok-openai/gpt-4o",
        messages=[ChatMessage(role="user", content="hi")],
    )
    assert req.model == "byok-openai/gpt-4o"


def test_usage_defaults_to_zero_decimals() -> None:
    u = Usage()
    assert u.cost_usd == Decimal(0)
    assert u.cost_rub == Decimal(0)
    assert u.fx_rate_usd_to_rub == Decimal(0)


def test_embedding_request_accepts_string_or_list() -> None:
    e1 = EmbeddingRequest(provider_slug="yandexgpt", model="text-search-doc", input="hi")
    e2 = EmbeddingRequest(provider_slug="yandexgpt", model="text-search-doc", input=["a", "b"])
    assert isinstance(e1.input, str)
    assert isinstance(e2.input, list)


def test_provider_out_supported_features_literal_subset() -> None:
    p = ProviderOut(
        provider_slug="deepseek",
        display_name="DeepSeek",
        default_model="deepseek-chat",
        base_url="https://api.deepseek.com",
        is_byok_supported=True,
        supported_features=["chat", "tool_use"],
    )
    assert "chat" in p.supported_features
