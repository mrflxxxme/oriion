"""Unit tests for byok_service — fingerprint, encrypt-on-store, no plaintext echo."""

from __future__ import annotations

import hashlib
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
import structlog
from src.llm_gateway.services.byok_service import fingerprint, store_byok_key


def test_fingerprint_is_sha256_first_eight() -> None:
    raw = "sk-test-1234"
    expected = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8]
    assert fingerprint(raw) == expected


def test_fingerprint_length_always_eight() -> None:
    assert len(fingerprint("any string")) == 8
    assert len(fingerprint("")) == 8
    assert len(fingerprint("x" * 1000)) == 8


@pytest.mark.asyncio
async def test_store_byok_key_encrypts_and_emits_event() -> None:
    """KMS.encrypt must be called; row.key_encrypted != plaintext; cloudevent emitted."""
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()

    kms = MagicMock()
    encrypted_blob = b"encrypted-ciphertext-blob-not-plaintext"
    kms.encrypt = AsyncMock(return_value=encrypted_blob)

    workspace_id = uuid4()
    created_by = uuid4()

    # Capture cloudevent emission via structlog.
    with structlog.testing.capture_logs() as logs:
        row: Any = await store_byok_key(
            session=session,
            kms=kms,
            workspace_id=workspace_id,
            provider_slug="openai",
            plaintext_key="sk-test-very-long-fake-key",  # gitleaks:allow
            label="Marketing OpenAI",
            created_by=created_by,
        )

    # Encryption happened with the plaintext bytes (not the row).
    kms.encrypt.assert_awaited_once()
    args, _ = kms.encrypt.call_args
    assert args[0] == b"sk-test-very-long-fake-key"

    # The row carries ciphertext + fingerprint, never plaintext.
    assert row.key_encrypted == encrypted_blob
    assert row.key_fingerprint == fingerprint("sk-test-very-long-fake-key")
    assert row.workspace_id == workspace_id

    # cloudevent emission.
    ce = next(log for log in logs if log.get("ce_type", "").endswith("byok.created.v1"))
    assert ce["data"]["provider_slug"] == "openai"
    assert ce["data"]["label"] == "Marketing OpenAI"
    # No plaintext anywhere in the event payload.
    assert "sk-test" not in str(ce["data"])
