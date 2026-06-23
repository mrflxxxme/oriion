"""Published T-credit rate (read-only).

Wave 0-1 operative facts (ADR-008):
  * 1 T-credit = 1 RUB (Wave-0 ledger invariant — see llm_gateway.billing_service).
  * role_multiplier = 1x for all roles (3x for the Western stack lands Wave 2+).
  * FX USD->RUB is the pinned ``FX_RATE_USD_TO_RUB`` (live ЦБ feed deferred to W2).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from src.llm_gateway.services.pricing_service import get_fx_rate

RUB_PER_CREDIT = Decimal("1")
ROLE_MULTIPLIER = Decimal("1")
WAVE = "0-1"


@dataclass(frozen=True, slots=True)
class CreditRate:
    rub_per_credit: Decimal
    fx_rate_usd_to_rub: Decimal
    role_multiplier: Decimal
    wave: str


def get_credit_rate() -> CreditRate:
    return CreditRate(
        rub_per_credit=RUB_PER_CREDIT,
        fx_rate_usd_to_rub=get_fx_rate(),
        role_multiplier=ROLE_MULTIPLIER,
        wave=WAVE,
    )
