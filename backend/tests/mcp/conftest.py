"""mcp-specific pytest fixtures.

Provides a minimal in-process Redis fake covering only the operations
ToolRateLimiter uses (EVAL the INCR+EXPIRE Lua) and registers the `live`
marker so ``-m "not live"`` can deselect Wave 1+ live-network tests
without tripping ``--strict-markers``.
"""

from __future__ import annotations

import time
from typing import Any

import pytest

# mcp models declare cross-schema string FKs (e.g. ConnectorCredential.workspace_id
# -> "multitenancy.workspaces.id"). Importing the target model registers its Table
# in Base.metadata so SQLAlchemy can resolve the FK when the `tests/mcp` subtree
# runs in ISOLATION (the per-module coverage gate). The app loads every model at
# startup, but an isolated test run does not — which made test_workspace_fk_cascades
# order-dependent (green on the full suite, red when tests/mcp ran alone).
import src.multitenancy.models  # noqa: F401  (SQLAlchemy model registration)


def pytest_configure(config: pytest.Config) -> None:
    """Register the `live` marker locally so strict-markers passes.

    Wave 0 has no live tests yet; the marker is reserved so Wave 1+ can
    add them without a pyproject change. Phase 00.4 spec calls for live
    tests behind ``BRAVE_SEARCH_API_KEY`` / ``YANDEX_SEARCH_API_KEY``.
    """
    config.addinivalue_line(
        "markers",
        "live: tests that hit real third-party APIs (deselect with '-m \"not live\"')",
    )


class FakeRedis:
    """Minimal Redis stand-in for ToolRateLimiter.

    Implements only `eval` (the INCR+EXPIRE Lua) — mirrors the contract
    `iam.tests.conftest.FakeRedis` provides. Tests that need additional
    Redis ops should extend this class rather than reach for fakeredis.
    """

    def __init__(self) -> None:
        self._store: dict[str, int] = {}
        self._expiry: dict[str, float] = {}

    def _purge(self) -> None:
        now = time.monotonic()
        expired = [k for k, t in self._expiry.items() if t <= now]
        for k in expired:
            self._store.pop(k, None)
            self._expiry.pop(k, None)

    async def eval(self, script: str, numkeys: int, *args: Any) -> Any:
        """Emulate the INCR + EXPIRE-on-first-hit Lua script."""
        self._purge()
        key = args[0]
        window_seconds = int(args[1])
        current = self._store.get(key, 0) + 1
        self._store[key] = current
        if current == 1:
            self._expiry[key] = time.monotonic() + window_seconds
        ttl = max(int(self._expiry.get(key, 0) - time.monotonic()), 0)
        return [current, ttl]


@pytest.fixture
def fake_redis() -> FakeRedis:
    return FakeRedis()
