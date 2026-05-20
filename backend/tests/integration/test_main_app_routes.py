"""Router-mount smoke for src.main:app.

Phase 00.5b Commit 2: a single positive-smoke that asserts every router we
intentionally include in main.py is reachable at its expected path under
/api/v1. This is the F-P5-5 documented convention's "mount-smoke" half —
mini-app router unit tests stay in their bounded-context test folders; this
file catches the regression where a router accidentally drops from main.py.

The test pulls the live ``app`` object from ``src.main`` and inspects
``app.routes`` — it does NOT make HTTP calls, so it stays in the unit
suite (deselected by ``@pytest.mark.integration``-only filters but
selected by the default ``not live`` filter) and contributes to the
``_shared`` per-module coverage gate.
"""

from __future__ import annotations

from typing import Final

import pytest
from src.main import app
from starlette.routing import Route

# Each entry is `(path, http_method)`. Methods chosen to be the canonical
# verb the router defines for that path — POST for create, GET for read.
# If a router adds new endpoints, this checklist stays as the minimal
# proof-of-mount; full endpoint coverage lives in the per-router unit tests.
_EXPECTED_ROUTES: Final[list[tuple[str, str]]] = [
    # iam (Phase 00.2)
    ("/api/v1/auth/register", "POST"),
    ("/api/v1/auth/login", "POST"),
    ("/api/v1/auth/logout", "POST"),
    ("/api/v1/auth/refresh", "POST"),
    ("/api/v1/users/me", "GET"),
    # multitenancy (Phase 00.5b Commit 2)
    ("/api/v1/workspaces", "POST"),
    ("/api/v1/workspaces", "GET"),
    ("/api/v1/workspaces/{workspace_id}/cells", "GET"),
    # llm_gateway (Phase 00.5b Commit 2)
    ("/api/v1/llm/chat/completions", "POST"),
    ("/api/v1/llm/embeddings", "POST"),
    ("/api/v1/llm/byok-keys", "GET"),
    ("/api/v1/llm/providers", "GET"),
    ("/api/v1/llm/usage", "GET"),
]


def _route_index() -> dict[tuple[str, str], Route]:
    """Build a {(path, method): Route} lookup from the live app."""
    index: dict[tuple[str, str], Route] = {}
    for r in app.routes:
        if not isinstance(r, Route):
            continue
        for method in r.methods or set():
            index[(r.path, method)] = r
    return index


@pytest.mark.parametrize(("path", "method"), _EXPECTED_ROUTES)
def test_router_mounted_under_api_v1(path: str, method: str) -> None:
    """Each expected (path, method) pair MUST be present on app.routes."""
    index = _route_index()
    assert (path, method) in index, (
        f"Expected {method} {path} to be mounted by src.main but it is "
        f"absent. Either a router dropped from main.include_router() or "
        f"its prefix/path changed — check src/main.py + the router module."
    )


def test_all_routers_mounted_under_api_v1() -> None:
    """Aggregate smoke — fail loud with one shot listing all gaps.

    The parametrised variant above pinpoints the missing pair; this one
    pretty-prints a single error message that's easier to skim in CI logs
    when more than one route is missing simultaneously (e.g. somebody
    deleted ``app.include_router(byok_router, ...)`` and ``providers_router``
    in the same commit).
    """
    index = _route_index()
    missing = [pair for pair in _EXPECTED_ROUTES if pair not in index]
    assert not missing, "Missing routes on src.main:app — " + ", ".join(
        f"{m} {p}" for p, m in missing
    )


def test_health_endpoint_present() -> None:
    """The /health probe is the contract gate for compose healthchecks."""
    index = _route_index()
    assert ("/health", "GET") in index
