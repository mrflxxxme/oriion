"""BYOK key custody — encrypt, fingerprint, persist, emit, decrypt-on-demand.

Per llm-gateway invariants #1 and #6: plaintext key is never stored; only
``key_fingerprint = sha256(plaintext)[:8]`` is surfaced in API responses.
"""

from __future__ import annotations

import hashlib
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.llm_gateway import events as gateway_events
from src.llm_gateway.exceptions import BYOKKeyNotFound
from src.llm_gateway.models import BYOKKey
from src.llm_gateway.services.kms_provider import KMSProvider


def fingerprint(plaintext_key: str) -> str:
    """Public-safe fingerprint: ``sha256(plaintext)[:8]``."""
    return hashlib.sha256(plaintext_key.encode("utf-8")).hexdigest()[:8]


async def store_byok_key(
    session: AsyncSession,
    kms: KMSProvider,
    *,
    workspace_id: UUID,
    provider_slug: str,
    plaintext_key: str,
    label: str,
    created_by: UUID,
    monthly_quota_usd: Decimal | None = None,
) -> BYOKKey:
    """Encrypt + persist + emit a new BYOK key row.

    Args:
        kms: KMSProvider — encrypt is awaited; plaintext_key is discarded
            from local scope immediately after.
    """
    ciphertext = await kms.encrypt(plaintext_key.encode("utf-8"))
    fp = fingerprint(plaintext_key)
    # Caller is expected to scrub plaintext_key after this point — nothing
    # else inside the gateway retains a reference.

    row = BYOKKey(
        workspace_id=workspace_id,
        provider_slug=provider_slug,
        key_encrypted=ciphertext,
        key_fingerprint=fp,
        label=label,
        monthly_quota_usd=monthly_quota_usd,
        created_by=created_by,
    )
    session.add(row)
    await session.flush()  # materialize row.id

    await gateway_events.emit_byok_created(
        byok_key_id=row.id,
        workspace_id=workspace_id,
        provider_slug=provider_slug,
        label=label,
        created_by=created_by,
    )
    return row


async def get_byok_key_plaintext(
    session: AsyncSession,
    kms: KMSProvider,
    *,
    byok_key_id: UUID,
    workspace_id: UUID,
) -> tuple[BYOKKey, str]:
    """Decrypt-on-demand. Returns (row, plaintext_key). Caller must not cache.

    Args:
        workspace_id: belt-and-suspenders RLS check (the DB policy also
            filters by workspace_id GUC). If the key isn't found within the
            workspace, raises ``BYOKKeyNotFound``.
    """
    stmt = select(BYOKKey).where(
        BYOKKey.id == byok_key_id,
        BYOKKey.workspace_id == workspace_id,
        BYOKKey.revoked_at.is_(None),
        BYOKKey.is_active.is_(True),
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise BYOKKeyNotFound(f"BYOK key {byok_key_id} not found for workspace.")
    plaintext_bytes = await kms.decrypt(row.key_encrypted)
    return row, plaintext_bytes.decode("utf-8")


async def list_active_keys(
    session: AsyncSession,
    *,
    workspace_id: UUID,
) -> list[BYOKKey]:
    """List non-revoked BYOK keys for the current workspace."""
    stmt = (
        select(BYOKKey)
        .where(
            BYOKKey.workspace_id == workspace_id,
            BYOKKey.revoked_at.is_(None),
        )
        .order_by(BYOKKey.created_at.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def revoke_byok_key(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    byok_key_id: UUID,
) -> None:
    """Soft-revoke via revoked_at + is_active=False."""
    from datetime import UTC, datetime

    stmt = select(BYOKKey).where(
        BYOKKey.id == byok_key_id,
        BYOKKey.workspace_id == workspace_id,
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise BYOKKeyNotFound(f"BYOK key {byok_key_id} not found for workspace.")
    row.revoked_at = datetime.now(UTC)
    row.is_active = False
    await session.flush()
