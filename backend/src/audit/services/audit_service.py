"""AuditService + module-level emit_audit_event.

Signature contract
==================
``emit_audit_event(...)`` is a **strict superset** of the stub at
``src/_stubs/audit.py::emit_audit_event``:

  stub signature (Phase 00.2 / Wave 0 transition):
      async def emit_audit_event(
          actor_type: str,
          actor_id: UUID,
          action: str,
          resource_type: str,
          resource_id: UUID | None = None,
          payload: dict[str, Any] | None = None,
          ip: str | None = None,
          user_agent: str | None = None,
      ) -> None

  real impl adds keyword-only extras (defaulted so all stub callers still
  work) plus relaxes ``resource_type`` to optional so non-resource events
  (e.g. ``iam.session.created`` w/ resource_type='session' but also pure
  control-plane events without one) compose cleanly:

      async def emit_audit_event(
          actor_type: str,
          actor_id: UUID,
          action: str,
          resource_type: str | None = None,
          resource_id: UUID | None = None,
          payload: dict[str, Any] | None = None,
          ip: str | None = None,
          user_agent: str | None = None,
          *,
          session: AsyncSession | None = None,
          workspace_id: UUID | None = None,
          cell_id: UUID | None = None,
      ) -> None

  The compatibility test (``test_emit_audit_event_stub_compat.py``) asserts
  every stub parameter — name + default semantics — is present here.

Behaviour
=========
* If ``session`` is provided: INSERT into ``audit.audit_log`` via
  ``AuditRepository`` in the caller's transaction. Caller commits.
* If ``session`` is None: fall back to a structlog record tagged
  ``audit_event=True`` (matches Phase 00.2 stub behaviour exactly so
  pre-00.2.5 callers keep working).
* In **both** modes we also call ``emit_cloudevent`` so observability
  consumers see the event regardless of DB write path.

CloudEvent envelope
===================
We use one canonical ``ce_type`` — ``oriion.audit.event.recorded.v1`` —
and let consumers discriminate on ``data.action``. This keeps the
events.yaml registry to a single entry per context (vs N entries per
audit action) while preserving full discriminator information in the
payload.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

import structlog

from src._shared.cloudevents import emit_cloudevent
from src.audit.repositories.audit_repository import AuditRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

__all__ = ["AuditService", "emit_audit_event"]

_logger = structlog.get_logger(__name__)

_AUDIT_CE_TYPE = "oriion.audit.event.recorded.v1"
_AUDIT_CE_SOURCE = "oriion://contexts/audit"


class AuditService:
    """DI-friendly wrapper around AuditRepository.

    Use this when a caller already owns an AsyncSession via FastAPI deps
    and wants a tidy collaborator object (testable via repo mock).
    The free-function ``emit_audit_event`` below is the public entrypoint
    that the rest of the codebase imports.
    """

    def __init__(self, repo: AuditRepository) -> None:
        self._repo = repo

    async def record(
        self,
        *,
        actor_type: str,
        actor_id: UUID | None,
        action: str,
        resource_type: str | None = None,
        resource_id: UUID | None = None,
        cell_id: UUID | None = None,
        workspace_id: UUID | None = None,
        payload: dict[str, Any] | None = None,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        await self._repo.insert(
            actor_type=actor_type,
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            cell_id=cell_id,
            workspace_id=workspace_id,
            payload=payload,
            ip=ip,
            user_agent=user_agent,
        )
        await _emit_cloudevent_for_action(
            action=action,
            actor_type=actor_type,
            actor_id=actor_id,
            resource_type=resource_type,
            resource_id=resource_id,
            cell_id=cell_id,
            workspace_id=workspace_id,
            payload=payload,
            ip=ip,
            user_agent=user_agent,
        )


async def _emit_cloudevent_for_action(
    *,
    action: str,
    actor_type: str,
    actor_id: UUID | None,
    resource_type: str | None,
    resource_id: UUID | None,
    cell_id: UUID | None,
    workspace_id: UUID | None,
    payload: dict[str, Any] | None,
    ip: str | None,
    user_agent: str | None,
) -> None:
    """Build the canonical CloudEvent data dict and emit."""
    data: dict[str, Any] = {
        "action": action,
        "actor_type": actor_type,
        "actor_id": str(actor_id) if actor_id is not None else None,
        "resource_type": resource_type,
        "resource_id": str(resource_id) if resource_id is not None else None,
        "cell_id": str(cell_id) if cell_id is not None else None,
        "workspace_id": str(workspace_id) if workspace_id is not None else None,
        "payload": payload,
        "ip": ip,
        "user_agent": user_agent,
    }
    await emit_cloudevent(
        ce_type=_AUDIT_CE_TYPE,
        source=_AUDIT_CE_SOURCE,
        data=data,
        subject=action,
    )


async def emit_audit_event(
    actor_type: str,
    actor_id: UUID,
    action: str,
    resource_type: str | None = None,
    resource_id: UUID | None = None,
    payload: dict[str, Any] | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
    *,
    session: AsyncSession | None = None,
    workspace_id: UUID | None = None,
    cell_id: UUID | None = None,
) -> None:
    """Emit an audit event.

    Signature is a strict superset of ``src._stubs.audit.emit_audit_event``
    so Phase 00.2.5 swap is a pure import replacement.

    Args:
        actor_type: ``user`` | ``agent`` | ``system``.
        actor_id: UUID of the actor. System events pass a synthetic UUID
            (callers' responsibility — DDL allows NULL but Phase 00.2 stub
            requires UUID, so we keep that contract here).
        action: Dotted action name, e.g. ``iam.user.registered``.
        resource_type: Optional resource kind (e.g. ``user``, ``workspace``).
            Stub had this as required ``str``; we relax to optional so 00.4
            control-plane events can omit it.
        resource_id: Optional UUID of the resource the action touched.
        payload: Optional JSON-serialisable extra context.
        ip: Optional client IP (stored as inet).
        user_agent: Optional client UA string.
        session: Optional AsyncSession — when present we INSERT into
            ``audit.audit_log`` inside the caller's TX. When None we
            fall back to the Phase 00.2 stub behaviour (structlog only).
        workspace_id: Optional tenant scope (added in real impl).
        cell_id: Optional cell scope (added in real impl).
    """
    if session is not None:
        repo = AuditRepository(session)
        await repo.insert(
            actor_type=actor_type,
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            cell_id=cell_id,
            workspace_id=workspace_id,
            payload=payload,
            ip=ip,
            user_agent=user_agent,
        )
    else:
        # Stub-compatible structlog fallback. Tests assert on
        # ``audit_event=True`` so this path stays observable end-to-end.
        _logger.bind(audit_event=True).info(
            "audit.recorded",
            action=action,
            actor_id=str(actor_id),
            actor_type=actor_type,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            payload=payload,
            ip=ip,
            user_agent=user_agent,
            workspace_id=str(workspace_id) if workspace_id else None,
            cell_id=str(cell_id) if cell_id else None,
        )

    await _emit_cloudevent_for_action(
        action=action,
        actor_type=actor_type,
        actor_id=actor_id,
        resource_type=resource_type,
        resource_id=resource_id,
        cell_id=cell_id,
        workspace_id=workspace_id,
        payload=payload,
        ip=ip,
        user_agent=user_agent,
    )
