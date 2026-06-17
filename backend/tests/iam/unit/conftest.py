"""iam.unit-scope fixtures.

Phase 00.2.5 swap-side-effect: auth_service + consent_service no longer
go through the structlog-only stub for ``emit_audit_event`` — they call
the real impl which tries to INSERT into ``audit.audit_log`` via the
caller's session. Unit tests pass an AsyncMock session that doesn't
actually accept ``await self._session.flush()`` cleanly, producing
PytestUnraisableExceptionWarning (promoted to error by the
project-wide ``filterwarnings=["error"]``).

The integration-tier tests cover the real audit-write path against a
testcontainers PG; here we autouse-patch ``emit_audit_event`` at the
two import sites so unit tests stay narrowly focused on orchestration
without dragging in the audit repo's session contract.
"""

from __future__ import annotations

from collections.abc import Iterator
from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture(autouse=True)
def _stub_emit_audit_event() -> Iterator[None]:
    """Replace emit_audit_event at the iam service modules' import sites.

    auth_service, account_recovery_service and consent_service each do
    ``from src.audit.services.audit_service import emit_audit_event`` —
    patching at those names is name-bound, so this fixture leaves the
    real impl available for anyone who imports the function directly.
    (account_recovery_service was split out of auth_service for the
    file-size canon; its recovery flows carry the audit calls.)
    """
    with (
        patch("src.iam.services.auth_service.emit_audit_event", AsyncMock()),
        patch("src.iam.services.account_recovery_service.emit_audit_event", AsyncMock()),
        patch("src.iam.services.consent_service.emit_audit_event", AsyncMock()),
    ):
        yield
