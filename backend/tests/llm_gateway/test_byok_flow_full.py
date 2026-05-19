"""AC6 — BYOK flow full integration: encrypt → persist → decrypt → proxy call.

Marked `integration` because the full flow normally needs Postgres; this
particular variant uses an in-memory fake session so it runs in the unit
tier, but keeps the integration mark for organisational consistency with
the spec (test name was reserved).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from src.llm_gateway.providers.byok_proxy import BYOKProxyProvider, parse_byok_model
from src.llm_gateway.services.byok_service import (
    fingerprint,
    get_byok_key_plaintext,
    store_byok_key,
)
from src.llm_gateway.services.kms_provider import LocalAESKMS


class _FakeSession:
    def __init__(self) -> None:
        self.added: list[Any] = []

    def add(self, row: Any) -> None:
        if hasattr(row, "id") and row.id is None:
            row.id = uuid4()
        self.added.append(row)

    async def flush(self) -> None:
        for row in self.added:
            if hasattr(row, "id") and row.id is None:
                row.id = uuid4()

    async def execute(self, _stmt: Any) -> Any:
        # Return the most-recently stored BYOK key — sufficient for the
        # decrypt-on-demand path used by get_byok_key_plaintext.
        scalar_obj = AsyncMock()
        last_row = self.added[-1] if self.added else None
        scalar_obj.scalar_one_or_none = lambda: last_row
        return scalar_obj


@pytest.mark.asyncio
@pytest.mark.integration
async def test_byok_flow_full(master_key_bytes: bytes) -> None:
    """End-to-end: store_byok_key encrypts → get_byok_key_plaintext decrypts
    → BYOKProxyProvider can be constructed with the recovered plaintext."""
    session = _FakeSession()
    kms = LocalAESKMS(master_key=master_key_bytes)
    workspace_id = uuid4()
    plaintext_key = "sk-test-byok-fake-key-1234567890"  # gitleaks:allow

    # 1) Store
    row = await store_byok_key(
        session=session,  # type: ignore[arg-type]
        kms=kms,
        workspace_id=workspace_id,
        provider_slug="openai",
        plaintext_key=plaintext_key,
        label="Marketing OpenAI",
        created_by=uuid4(),
    )
    assert row.key_fingerprint == fingerprint(plaintext_key)
    assert row.key_encrypted != plaintext_key.encode("utf-8")

    # 2) Retrieve + decrypt
    _row, recovered = await get_byok_key_plaintext(
        session=session,  # type: ignore[arg-type]
        kms=kms,
        byok_key_id=row.id,
        workspace_id=workspace_id,
    )
    assert recovered == plaintext_key

    # 3) Construct BYOK proxy — should not raise; payload not exposed.
    upstream_provider, upstream_model = parse_byok_model("byok-openai/gpt-4o")
    proxy = BYOKProxyProvider(
        plaintext_key=recovered,
        upstream_provider_slug=upstream_provider,
    )
    assert proxy.name == "byok"
    assert upstream_model == "gpt-4o"


def test_parse_byok_model_validates_format() -> None:
    with pytest.raises(ValueError, match="not a BYOK model"):
        parse_byok_model("deepseek-chat")
    with pytest.raises(ValueError, match="must be 'byok-<provider>/<model>'"):
        parse_byok_model("byok-openai")


def test_byok_proxy_unknown_provider_raises() -> None:
    with pytest.raises(ValueError, match="not supported"):
        BYOKProxyProvider(
            plaintext_key="x",
            upstream_provider_slug="exotic-provider",
        )
