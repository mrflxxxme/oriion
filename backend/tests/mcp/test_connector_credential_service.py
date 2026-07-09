"""Unit: connector_credential_service — encrypt-on-store, fingerprint, decrypt, revoke.

Uses the real ``LocalAESKMS`` (round-trips ciphertext) + an in-memory fake session
whose ``execute`` returns a configurable scalar. The DB WHERE-clause filtering
(revoked/inactive rows excluded) is modelled by the fake returning ``None``.
"""

from __future__ import annotations

import hashlib
from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from src.llm_gateway.services.kms_provider import LocalAESKMS
from src.mcp.exceptions import ConnectorCredentialNotFound
from src.mcp.services import connector_credential_service as svc

_MASTER_KEY = bytes(range(32))
_SECRET = "1234567890:AA-fake-telegram-bot-token-value"  # gitleaks:allow


class _FakeSession:
    def __init__(self) -> None:
        self.added: list[Any] = []
        self.next_scalar: Any = None

    def add(self, row: Any) -> None:
        if getattr(row, "id", None) is None:
            row.id = uuid4()
        self.added.append(row)

    async def flush(self) -> None:
        for row in self.added:
            if getattr(row, "id", None) is None:
                row.id = uuid4()

    async def execute(self, _stmt: Any) -> Any:
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=self.next_scalar)
        return result


def test_fingerprint_is_sha256_first_eight() -> None:
    expected = hashlib.sha256(_SECRET.encode("utf-8")).hexdigest()[:8]
    assert svc.fingerprint(_SECRET) == expected
    assert len(svc.fingerprint(_SECRET)) == 8
    assert len(svc.fingerprint("")) == 8


@pytest.mark.asyncio
async def test_store_encrypts_and_never_persists_plaintext() -> None:
    session = _FakeSession()
    kms = LocalAESKMS(master_key=_MASTER_KEY)
    row = await svc.store_credential(
        session,  # type: ignore[arg-type]
        kms,
        workspace_id=uuid4(),
        connector_slug="telegram-bot",
        plaintext_secret=_SECRET,
        label="main",
        created_by=uuid4(),
    )
    # Ciphertext ≠ plaintext, and the plaintext bytes do not appear inside it.
    assert row.cred_encrypted != _SECRET.encode("utf-8")
    assert _SECRET.encode("utf-8") not in row.cred_encrypted
    # Fingerprint is the public-safe digest, not the secret.
    assert row.cred_fingerprint == svc.fingerprint(_SECRET)
    assert row.cred_fingerprint != _SECRET
    assert len(session.added) == 1


@pytest.mark.asyncio
async def test_store_then_get_plaintext_round_trips() -> None:
    session = _FakeSession()
    kms = LocalAESKMS(master_key=_MASTER_KEY)
    workspace_id = uuid4()
    row = await svc.store_credential(
        session,  # type: ignore[arg-type]
        kms,
        workspace_id=workspace_id,
        connector_slug="imap-smtp",
        plaintext_secret=_SECRET,
        label="mailbox",
        created_by=uuid4(),
    )

    session.next_scalar = row
    got_row, recovered = await svc.get_credential_plaintext(
        session,  # type: ignore[arg-type]
        kms,
        credential_id=row.id,
        workspace_id=workspace_id,
    )
    assert got_row is row
    assert recovered == _SECRET


@pytest.mark.asyncio
async def test_get_plaintext_missing_raises() -> None:
    session = _FakeSession()
    session.next_scalar = None
    with pytest.raises(ConnectorCredentialNotFound):
        await svc.get_credential_plaintext(
            session,  # type: ignore[arg-type]
            LocalAESKMS(master_key=_MASTER_KEY),
            credential_id=uuid4(),
            workspace_id=uuid4(),
        )


@pytest.mark.asyncio
async def test_revoke_soft_sets_flags() -> None:
    session = _FakeSession()
    kms = LocalAESKMS(master_key=_MASTER_KEY)
    workspace_id = uuid4()
    row = await svc.store_credential(
        session,  # type: ignore[arg-type]
        kms,
        workspace_id=workspace_id,
        connector_slug="yandex-disk",
        plaintext_secret=_SECRET,
        label="disk",
        created_by=uuid4(),
    )
    session.next_scalar = row
    await svc.revoke_credential(session, workspace_id=workspace_id, credential_id=row.id)  # type: ignore[arg-type]
    assert row.is_active is False
    assert row.revoked_at is not None


@pytest.mark.asyncio
async def test_revoke_missing_raises() -> None:
    session = _FakeSession()
    session.next_scalar = None
    with pytest.raises(ConnectorCredentialNotFound):
        await svc.revoke_credential(session, workspace_id=uuid4(), credential_id=uuid4())  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_revoked_credential_is_not_retrievable() -> None:
    """After revoke, the WHERE clause (revoked_at IS NULL AND is_active) excludes
    the row — modelled here by the fake returning None → NotFound."""
    session = _FakeSession()
    kms = LocalAESKMS(master_key=_MASTER_KEY)
    workspace_id = uuid4()
    row = await svc.store_credential(
        session,  # type: ignore[arg-type]
        kms,
        workspace_id=workspace_id,
        connector_slug="telegram-bot",
        plaintext_secret=_SECRET,
        label="main",
        created_by=uuid4(),
    )
    session.next_scalar = row
    await svc.revoke_credential(session, workspace_id=workspace_id, credential_id=row.id)  # type: ignore[arg-type]

    session.next_scalar = None  # DB filter now excludes the revoked row
    with pytest.raises(ConnectorCredentialNotFound):
        await svc.get_credential_plaintext(
            session,  # type: ignore[arg-type]
            kms,
            credential_id=row.id,
            workspace_id=workspace_id,
        )
