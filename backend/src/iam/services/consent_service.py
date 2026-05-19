"""FZ-152 consent grant/revoke ledger.

Invariant 6: pdn consent is mandatory before register completes; version
is pinned at grant time and never mutated. Each grant/revoke emits
oriion.iam.user.consent_recorded.v1 + writes an audit row into
audit.audit_log inside the caller's TX (Phase 00.2.5 swap to real impl).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.audit.services.audit_service import emit_audit_event
from src.iam.events import emit_consent_recorded
from src.iam.repositories.consent_repository import ConsentRepository

ConsentKind = Literal["pdn", "marketing", "tos"]


class ConsentService:
    def __init__(
        self,
        consent_repo: ConsentRepository,
        consent_version: str,
        *,
        session: AsyncSession,
    ) -> None:
        self._repo = consent_repo
        self._version = consent_version
        # Held so emit_audit_event inserts into audit.audit_log inside the
        # request's outer TX (instead of falling back to structlog-only).
        self._session = session

    async def record(
        self,
        *,
        user_id: UUID,
        kind: ConsentKind,
        ip: str | None,
        user_agent: str | None,
    ) -> None:
        row = await self._repo.record(
            user_id=user_id,
            kind=kind,
            version=self._version,
            ip=ip,
            user_agent=user_agent,
        )
        recorded_at = row.granted_at or datetime.now(UTC)
        await emit_consent_recorded(
            user_id=user_id,
            kind=kind,
            version=self._version,
            action="granted",
            recorded_at=recorded_at,
        )
        await emit_audit_event(
            actor_type="user",
            actor_id=user_id,
            action="iam.consent.granted",
            resource_type="consent",
            resource_id=row.id,
            payload={"kind": kind, "version": self._version},
            ip=ip,
            user_agent=user_agent,
            session=self._session,
        )

    async def revoke(
        self,
        *,
        user_id: UUID,
        kind: ConsentKind,
        ip: str | None,
        user_agent: str | None,
    ) -> None:
        await self._repo.revoke(user_id=user_id, kind=kind)
        now = datetime.now(UTC)
        await emit_consent_recorded(
            user_id=user_id,
            kind=kind,
            version=self._version,
            action="revoked",
            recorded_at=now,
        )
        await emit_audit_event(
            actor_type="user",
            actor_id=user_id,
            action="iam.consent.revoked",
            resource_type="consent",
            resource_id=None,
            payload={"kind": kind, "version": self._version},
            ip=ip,
            user_agent=user_agent,
            session=self._session,
        )
