"""Connector credential custody — encrypt, fingerprint, persist, decrypt-on-demand.

Phase 01.9b connector security core (PASS A). Mirrors
``llm_gateway.services.byok_service`` for third-party connector secrets
(telegram-bot token, yandex-disk OAuth token, imap-smtp password). Invariants:

* The plaintext secret is NEVER stored or logged — only the AES-256-GCM ciphertext
  (via the shared ``get_kms_provider()``) and a public-safe
  ``cred_fingerprint = sha256(plaintext)[:8]`` reach the DB / API surface.
* ``get_credential_plaintext`` decrypts on demand with a belt-and-suspenders
  ``workspace_id`` filter ON TOP of Postgres RLS, and refuses revoked/inactive rows
  (raises ``ConnectorCredentialNotFound``).

Structured connectors (e.g. imap-smtp host/user/password) serialize their secret to
a single string upstream (pass B) before ``store_credential`` — this custody layer
treats the plaintext as an opaque UTF-8 string.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.llm_gateway.services.kms_provider import KMSProvider
from src.mcp.exceptions import ConnectorCredentialNotFound
from src.mcp.models import ConnectorCredential

logger = structlog.get_logger(__name__)


def fingerprint(plaintext_secret: str) -> str:
    """Public-safe fingerprint: ``sha256(plaintext)[:8]`` (not reversible)."""
    return hashlib.sha256(plaintext_secret.encode("utf-8")).hexdigest()[:8]


async def store_credential(
    session: AsyncSession,
    kms: KMSProvider,
    *,
    workspace_id: UUID,
    connector_slug: str,
    plaintext_secret: str,
    label: str,
    created_by: UUID,
) -> ConnectorCredential:
    """Encrypt + persist a new connector credential row.

    The plaintext is encrypted via ``kms.encrypt`` and then dropped from local
    scope — nothing inside this module retains a reference. Only the ciphertext +
    the sha256[:8] fingerprint are written. Caller is expected to scrub its own
    ``plaintext_secret`` after this returns.
    """
    ciphertext = await kms.encrypt(plaintext_secret.encode("utf-8"))
    fp = fingerprint(plaintext_secret)

    row = ConnectorCredential(
        workspace_id=workspace_id,
        connector_slug=connector_slug,
        cred_encrypted=ciphertext,
        cred_fingerprint=fp,
        label=label,
        created_by=created_by,
    )
    session.add(row)
    await session.flush()  # materialize row.id

    # SECURITY: only non-secret metadata is logged — never the plaintext.
    logger.info(
        "mcp.connector_credential.stored",
        connector_slug=connector_slug,
        workspace_id=str(workspace_id),
        cred_fingerprint=fp,
        label=label,
    )
    return row


async def get_credential_plaintext(
    session: AsyncSession,
    kms: KMSProvider,
    *,
    credential_id: UUID,
    workspace_id: UUID,
) -> tuple[ConnectorCredential, str]:
    """Decrypt-on-demand. Returns ``(row, plaintext_secret)``. Caller must not cache.

    Args:
        workspace_id: belt-and-suspenders RLS check (the DB policy also filters by
            the ``app.current_workspace_id`` GUC). A credential that is missing,
            revoked, or inactive within the workspace raises
            ``ConnectorCredentialNotFound``.
    """
    stmt = select(ConnectorCredential).where(
        ConnectorCredential.id == credential_id,
        ConnectorCredential.workspace_id == workspace_id,
        ConnectorCredential.revoked_at.is_(None),
        ConnectorCredential.is_active.is_(True),
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise ConnectorCredentialNotFound(
            f"connector credential {credential_id} not found for workspace."
        )
    plaintext_bytes = await kms.decrypt(row.cred_encrypted)
    return row, plaintext_bytes.decode("utf-8")


async def list_active_credentials(
    session: AsyncSession,
    *,
    workspace_id: UUID,
) -> list[ConnectorCredential]:
    """List non-revoked connector credentials for the current workspace."""
    stmt = (
        select(ConnectorCredential)
        .where(
            ConnectorCredential.workspace_id == workspace_id,
            ConnectorCredential.revoked_at.is_(None),
        )
        .order_by(ConnectorCredential.created_at.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def revoke_credential(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    credential_id: UUID,
) -> None:
    """Soft-revoke via ``revoked_at`` + ``is_active=False``.

    Raises ``ConnectorCredentialNotFound`` when no row matches (id, workspace).
    """
    stmt = select(ConnectorCredential).where(
        ConnectorCredential.id == credential_id,
        ConnectorCredential.workspace_id == workspace_id,
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise ConnectorCredentialNotFound(
            f"connector credential {credential_id} not found for workspace."
        )
    row.revoked_at = datetime.now(UTC)
    row.is_active = False
    await session.flush()


__all__ = [
    "fingerprint",
    "get_credential_plaintext",
    "list_active_credentials",
    "revoke_credential",
    "store_credential",
]
