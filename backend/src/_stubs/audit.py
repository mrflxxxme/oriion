"""Stub for audit.emit_audit_event.

Signature is contract-locked per
.planning/_session-context/2026-05-17-architect-pr-3-way-parallel.md §Stub 2.

Real impl lands from Phase 00.3 at
backend/src/audit/services/audit_service.py and INSERTs into the
partitioned-by-month, append-only-via-trigger audit.audit_log table.
Integration phase 00.2.5 swaps the import.

Wave 0 behaviour: emit a structured log line tagged audit_event=True so
tests can assert on log records (no DB writes).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import structlog

logger = structlog.get_logger(__name__)


async def emit_audit_event(
    actor_type: str,
    actor_id: UUID,
    action: str,
    resource_type: str,
    resource_id: UUID | None = None,
    payload: dict[str, Any] | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Stub: writes a tagged structlog record. No DB write.

    Production behaviour (Phase 00.3):
        INSERT INTO audit.audit_log (
            actor_type, actor_id, action, resource_type, resource_id,
            payload, ip, user_agent, ts
        ) VALUES ($1, ..., NOW());

    Args mirror the real impl exactly so integration phase 00.2.5 is a
    pure import-replacement.
    """
    logger.bind(audit_event=True).info(
        "audit.stub",
        action=action,
        actor_id=str(actor_id),
        actor_type=actor_type,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id else None,
        payload=payload,
        ip=ip,
        user_agent=user_agent,
    )
