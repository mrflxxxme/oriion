"""Unit tests for pricing_service — Decimal-only cost computation."""

from __future__ import annotations

from decimal import Decimal

import pytest
from src.llm_gateway.services.pricing_service import (
    PROVIDER_PRICING_USD_PER_1K_TOKENS,
    calculate_cost_usd_and_rub,
    get_fx_rate,
)


def test_pricing_table_uses_decimal_only() -> None:
    for provider, models in PROVIDER_PRICING_USD_PER_1K_TOKENS.items():
        for model, prices in models.items():
            for direction, price in prices.items():
                assert isinstance(price, Decimal), (
                    f"{provider}/{model}/{direction} must be Decimal; "
                    f"got {type(price).__name__}"
                )


def test_calculate_cost_for_deepseek_chat() -> None:
    cost_usd, cost_rub = calculate_cost_usd_and_rub(
        "deepseek",
        "deepseek-chat",
        tokens_in=1000,
        tokens_out=1000,
        fx_rate=Decimal("100"),
    )
    # AC-W1-13 V4 refresh: deepseek-chat (V4-flash tier) — $0.27/1M in, $1.10/1M
    # out. 1k input @ 0.00027 + 1k output @ 0.00110 = 0.00137 USD.
    assert cost_usd == Decimal("0.001370")
    # 0.00137 * 100 = 0.137 RUB → quantize to (12,4) precision.
    assert cost_rub == Decimal("0.1370")


def test_calculate_cost_deepseek_v4_catalog_names_match_aliases() -> None:
    """The V4 catalog model names price identically to the logical aliases."""
    flash = calculate_cost_usd_and_rub(
        "deepseek", "deepseek-v4-flash", tokens_in=1000, tokens_out=1000, fx_rate=Decimal("100")
    )
    chat = calculate_cost_usd_and_rub(
        "deepseek", "deepseek-chat", tokens_in=1000, tokens_out=1000, fx_rate=Decimal("100")
    )
    assert flash == chat
    pro = calculate_cost_usd_and_rub(
        "deepseek", "deepseek-v4-pro", tokens_in=1000, tokens_out=1000, fx_rate=Decimal("100")
    )
    reasoner = calculate_cost_usd_and_rub(
        "deepseek", "deepseek-reasoner", tokens_in=1000, tokens_out=1000, fx_rate=Decimal("100")
    )
    assert pro == reasoner
    # pro tier (V4-pro) — $0.55/1M in, $2.19/1M out.
    assert pro[0] == Decimal("0.002740")


def test_calculate_cost_for_yandex_pro() -> None:
    cost_usd, cost_rub = calculate_cost_usd_and_rub(
        "yandexgpt",
        "yandexgpt-pro",
        tokens_in=500,
        tokens_out=500,
        fx_rate=Decimal("100"),
    )
    # 0.5 * 0.012 + 0.5 * 0.012 = 0.012 USD
    assert cost_usd == Decimal("0.012000")
    assert cost_rub == Decimal("1.2000")


def test_calculate_cost_unknown_provider_returns_zero() -> None:
    cost_usd, cost_rub = calculate_cost_usd_and_rub(
        "exotic-provider",
        "exotic-model",
        tokens_in=1000,
        tokens_out=1000,
        fx_rate=Decimal("100"),
    )
    assert cost_usd == Decimal(0)
    assert cost_rub == Decimal(0)


def test_calculate_cost_unknown_model_returns_zero() -> None:
    cost_usd, cost_rub = calculate_cost_usd_and_rub(
        "deepseek",
        "deepseek-not-a-real-model",
        tokens_in=1000,
        tokens_out=1000,
        fx_rate=Decimal("100"),
    )
    assert cost_usd == Decimal(0)
    assert cost_rub == Decimal(0)


def test_get_fx_rate_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FX_RATE_USD_TO_RUB", raising=False)
    assert get_fx_rate() == Decimal("100.0")


def test_get_fx_rate_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FX_RATE_USD_TO_RUB", "92.55")
    assert get_fx_rate() == Decimal("92.55")


def test_get_fx_rate_invalid_env_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FX_RATE_USD_TO_RUB", "not-a-number")
    assert get_fx_rate() == Decimal("100.0")


def test_quantization_matches_db_precision() -> None:
    """cost_usd → 6 fractional digits; cost_rub → 4 fractional digits."""
    cost_usd, cost_rub = calculate_cost_usd_and_rub(
        "openai",
        "gpt-4o",
        tokens_in=1234,
        tokens_out=567,
        fx_rate=Decimal("93.1234"),
    )
    # Assert quantize precision by inspecting exponent.
    assert cost_usd.as_tuple().exponent == -6
    assert cost_rub.as_tuple().exponent == -4
