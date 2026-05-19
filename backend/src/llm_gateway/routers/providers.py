"""GET /api/v1/llm/providers, GET /api/v1/llm/providers/status."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src._shared.db.session import get_db
from src.llm_gateway.models import LLMProviderConfig
from src.llm_gateway.schemas import (
    FeatureLiteral,
    ProviderOut,
    ProviderStatusOut,
)

router = APIRouter(prefix="/llm", tags=["providers"])


@router.get("/providers", response_model=list[ProviderOut])
async def list_providers(
    feature: FeatureLiteral | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> list[ProviderOut]:
    stmt = select(LLMProviderConfig).where(LLMProviderConfig.is_active.is_(True))
    rows = (await db.execute(stmt)).scalars().all()
    out: list[ProviderOut] = []
    for row in rows:
        if feature is not None and feature not in row.supported_features:
            continue
        out.append(
            ProviderOut(
                provider_slug=row.provider_slug,
                display_name=row.display_name,
                default_model=row.default_model,
                base_url=row.base_url,
                is_byok_supported=row.is_byok_supported,
                # Cast text[] to literal list — DB stores arbitrary strings,
                # but the contract restricts to the FeatureLiteral set.
                supported_features=[
                    f
                    for f in row.supported_features
                    if f
                    in {
                        "chat",
                        "embeddings",
                        "structured_output",
                        "tool_use",
                        "vision",
                    }
                ],
            )
        )
    return out


@router.get("/providers/status", response_model=list[ProviderStatusOut])
async def providers_status(
    db: AsyncSession = Depends(get_db),
) -> list[ProviderStatusOut]:
    """Per-provider health + circuit state.

    Wave 0 returns a static snapshot — health state is held in
    ``HealthMonitor`` (in-memory, single-process). Wave 1+ exposes Redis-backed
    cross-instance state.
    """
    stmt = select(LLMProviderConfig).where(LLMProviderConfig.is_active.is_(True))
    rows = (await db.execute(stmt)).scalars().all()
    now = datetime.now(UTC)
    return [
        ProviderStatusOut(
            provider_slug=row.provider_slug,
            state="healthy",  # Wave 0 stub — real state via HealthMonitor in Wave 1+
            circuit="closed",
            last_check=now,
        )
        for row in rows
    ]
