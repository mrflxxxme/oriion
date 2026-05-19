"""Additional byok_service coverage: list_active_keys, revoke, get_plaintext."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from src.llm_gateway.exceptions import BYOKKeyNotFound
from src.llm_gateway.models import BYOKKey
from src.llm_gateway.services.byok_service import (
    get_byok_key_plaintext,
    list_active_keys,
    revoke_byok_key,
    store_byok_key,
)
from src.llm_gateway.services.kms_provider import LocalAESKMS


class _Session:
    """Captures `add` + answers SELECTs deterministically."""

    def __init__(self, lookup_row: Any = None, scalars_rows: list[Any] | None = None) -> None:
        self.added: list[Any] = []
        self._lookup_row = lookup_row
        self._scalars_rows = scalars_rows or []
        self.flushes = 0

    def add(self, row: Any) -> None:
        if hasattr(row, "id") and row.id is None:
            row.id = uuid4()
        self.added.append(row)

    async def flush(self) -> None:
        self.flushes += 1
        for row in self.added:
            if hasattr(row, "id") and row.id is None:
                row.id = uuid4()

    async def execute(self, _stmt: Any) -> Any:
        result = MagicMock()
        # scalar_one_or_none returns _lookup_row.
        result.scalar_one_or_none = MagicMock(return_value=self._lookup_row)
        # scalars().all() returns _scalars_rows.
        scalars_obj = MagicMock()
        scalars_obj.all = MagicMock(return_value=self._scalars_rows)
        result.scalars = MagicMock(return_value=scalars_obj)
        return result


@pytest.mark.asyncio
async def test_get_byok_key_plaintext_decrypts_round_trip(master_key_bytes: bytes) -> None:
    kms = LocalAESKMS(master_key=master_key_bytes)
    plaintext = "sk-test-decrypt-roundtrip"  # gitleaks:allow

    # First store via the real path so we get an authentic ciphertext blob.
    store_session = _Session()
    workspace_id = uuid4()
    stored = await store_byok_key(
        session=store_session,  # type: ignore[arg-type]
        kms=kms,
        workspace_id=workspace_id,
        provider_slug="openai",
        plaintext_key=plaintext,
        label="Lookup test",
        created_by=uuid4(),
    )

    # Now look it up.
    session = _Session(lookup_row=stored)
    row, recovered = await get_byok_key_plaintext(
        session=session,  # type: ignore[arg-type]
        kms=kms,
        byok_key_id=stored.id,
        workspace_id=workspace_id,
    )
    assert row is stored
    assert recovered == plaintext


@pytest.mark.asyncio
async def test_get_byok_key_plaintext_missing_raises() -> None:
    session = _Session(lookup_row=None)
    with pytest.raises(BYOKKeyNotFound):
        await get_byok_key_plaintext(
            session=session,  # type: ignore[arg-type]
            kms=LocalAESKMS(master_key=b"0" * 32),
            byok_key_id=uuid4(),
            workspace_id=uuid4(),
        )


@pytest.mark.asyncio
async def test_list_active_keys_returns_repo_rows() -> None:
    rows = [
        BYOKKey(
            workspace_id=uuid4(),
            provider_slug="openai",
            key_encrypted=b"x",
            key_fingerprint="abcd1234",
            label="A",
            created_by=uuid4(),
        ),
    ]
    session = _Session(scalars_rows=rows)
    out = await list_active_keys(session=session, workspace_id=uuid4())  # type: ignore[arg-type]
    assert out == rows


@pytest.mark.asyncio
async def test_revoke_byok_key_sets_revoked_at_and_is_active_false() -> None:
    row = BYOKKey(
        workspace_id=uuid4(),
        provider_slug="openai",
        key_encrypted=b"x",
        key_fingerprint="abcd1234",
        label="To Revoke",
        created_by=uuid4(),
        is_active=True,
        revoked_at=None,
    )
    session = _Session(lookup_row=row)
    before = datetime.now(UTC)
    await revoke_byok_key(
        session=session,  # type: ignore[arg-type]
        workspace_id=uuid4(),
        byok_key_id=uuid4(),
    )
    assert row.is_active is False
    assert row.revoked_at is not None
    assert row.revoked_at >= before


@pytest.mark.asyncio
async def test_revoke_byok_key_missing_raises() -> None:
    session = _Session(lookup_row=None)
    with pytest.raises(BYOKKeyNotFound):
        await revoke_byok_key(
            session=session,  # type: ignore[arg-type]
            workspace_id=uuid4(),
            byok_key_id=uuid4(),
        )
