"""Decimal-only pricing table + USD/RUB cost computation.

ADR-018 (DeepSeek primary) amendment 2026-05-19 introduces a 3-currency
model:

    cost_usd = (tokens_in/1000 * input_usd) + (tokens_out/1000 * output_usd)
    cost_rub = cost_usd * fx_rate_usd_to_rub

The FX rate is read from ``FX_RATE_USD_TO_RUB`` env (Decimal-safe) and
pinned per-request inside the row. Wave 1+ swaps to a live FX feed.

Provider native price units:
    deepseek, openai, anthropic  → USD per 1k tokens
    yandex, gigachat             → RUB per 1k tokens (Russian providers)

For uniform billing every provider's prices are stored as USD-per-1k below;
RU-native prices are derived via the live FX rate baseline (no fixed multiplier
- the table holds an effective USD price that matches the RU vendor invoice
at the FX rate Oriion currently runs). When more accurate accounting is
needed (Wave 1+), the table can split USD/RUB columns.
"""

from __future__ import annotations

import os
from decimal import Decimal

PROVIDER_PRICING_USD_PER_1K_TOKENS: dict[str, dict[str, dict[str, Decimal]]] = {
    # DeepSeek — published USD pricing 2026-Q1 (deepseek.com/pricing).
    "deepseek": {
        "deepseek-chat": {
            "input": Decimal("0.00014"),
            "output": Decimal("0.00028"),
        },
        "deepseek-reasoner": {
            "input": Decimal("0.00055"),
            "output": Decimal("0.00220"),
        },
    },
    # YandexGPT — RUB-native; effective USD price assumes ~100 RUB/USD baseline.
    # Wave 1+ swaps to live FX in `pricing_table`.
    "yandexgpt": {
        "yandexgpt-pro": {
            "input": Decimal("0.012"),
            "output": Decimal("0.012"),
        },
        "yandexgpt-lite": {
            "input": Decimal("0.002"),
            "output": Decimal("0.002"),
        },
    },
    # GigaChat — RUB-native; same caveat as Yandex.
    "gigachat": {
        "GigaChat-Pro": {
            "input": Decimal("0.015"),
            "output": Decimal("0.015"),
        },
        "GigaChat-Max": {
            "input": Decimal("0.0195"),
            "output": Decimal("0.0195"),
        },
    },
    # OpenAI — published USD pricing 2026-Q1 (gpt-4o family).
    "openai": {
        "gpt-4o": {
            "input": Decimal("0.0025"),
            "output": Decimal("0.010"),
        },
        "gpt-4o-mini": {
            "input": Decimal("0.00015"),
            "output": Decimal("0.0006"),
        },
        "text-embedding-3-small": {
            "input": Decimal("0.00002"),
            "output": Decimal("0"),
        },
    },
    # Anthropic — Claude Sonnet 4.6 published pricing 2026-Q1.
    "anthropic": {
        "claude-sonnet-4-6": {
            "input": Decimal("0.003"),
            "output": Decimal("0.015"),
        },
        "claude-opus-4-7": {
            "input": Decimal("0.015"),
            "output": Decimal("0.075"),
        },
    },
}


_FX_DEFAULT = Decimal("100.0")


def get_fx_rate() -> Decimal:
    """Read FX rate from env (Decimal-safe) with default 100.0.

    Wave 1+ swaps this to a live FX feed (CBR daily snapshot).
    """
    raw = os.environ.get("FX_RATE_USD_TO_RUB")
    if not raw:
        return _FX_DEFAULT
    try:
        return Decimal(raw)
    except (ArithmeticError, ValueError):
        return _FX_DEFAULT


def calculate_cost_usd_and_rub(
    provider_slug: str,
    model: str,
    tokens_in: int,
    tokens_out: int,
    fx_rate: Decimal,
) -> tuple[Decimal, Decimal]:
    """Return ``(cost_usd, cost_rub)`` for a single LLM call.

    Unknown provider/model defaults to ``(Decimal(0), Decimal(0))`` so the
    gateway never raises on usage logging — billing reconciliation surfaces
    the row as zero-priced and the ops team can backfill via Wave 1+ pricing
    table. This avoids fail-closed on a new model's first request.
    """
    provider_table = PROVIDER_PRICING_USD_PER_1K_TOKENS.get(provider_slug)
    if provider_table is None:
        return Decimal(0), Decimal(0)
    model_prices = provider_table.get(model)
    if model_prices is None:
        return Decimal(0), Decimal(0)
    input_price = model_prices.get("input", Decimal(0))
    output_price = model_prices.get("output", Decimal(0))

    cost_usd = (Decimal(tokens_in) / Decimal(1000)) * input_price + (
        Decimal(tokens_out) / Decimal(1000)
    ) * output_price
    cost_rub = cost_usd * fx_rate
    # Quantize to schema precision: usd(10,6), rub(12,4).
    cost_usd_q = cost_usd.quantize(Decimal("0.000001"))
    cost_rub_q = cost_rub.quantize(Decimal("0.0001"))
    return cost_usd_q, cost_rub_q
