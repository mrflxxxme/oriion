"""Local fixtures + marker registration for llm_gateway test package.

`live` and `integration` markers are registered here so the parent pyproject
remains untouched (the integration marker is already declared globally;
registering it twice is a no-op). With `--strict-markers` on, unregistered
markers cause a collection error.
"""

from __future__ import annotations

import base64
import os
import secrets
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from src.llm_gateway.services.kms_provider import LocalAESKMS


def pytest_configure(config: pytest.Config) -> None:
    """Register llm_gateway-specific markers."""
    config.addinivalue_line(
        "markers",
        "live: tests that hit real provider APIs — require TBD_* env keys; "
        "skipped by default per Wave 0 CI policy.",
    )
    config.addinivalue_line(
        "markers",
        "integration: integration tests requiring docker-compose stack "
        "(deselect with '-m \"not integration\"').",
    )


@pytest.fixture
def master_key_bytes() -> bytes:
    """Stable 32-byte AES-256 key for KMS tests."""
    return b"0123456789abcdef0123456789abcdef"


@pytest.fixture(autouse=True)
def _isolated_byok_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provide a deterministic BYOK_MASTER_KEY_B64 env so KMSProvider tests
    do not depend on the developer's local environment.

    Also strips FX_RATE_USD_TO_RUB to keep pricing tests deterministic.
    """
    key = secrets.token_bytes(32)
    monkeypatch.setenv("BYOK_MASTER_KEY_B64", base64.b64encode(key).decode("ascii"))
    monkeypatch.delenv("FX_RATE_USD_TO_RUB", raising=False)
    monkeypatch.delenv("KMS_BACKEND", raising=False)


@pytest.fixture
def kms() -> LocalAESKMS:
    """Construct a LocalAESKMS using the autouse env above."""
    # Import inside the fixture so the env mutation above is in effect.
    from src.llm_gateway.services.kms_provider import LocalAESKMS

    raw = os.environ["BYOK_MASTER_KEY_B64"]
    return LocalAESKMS(master_key=base64.b64decode(raw))
