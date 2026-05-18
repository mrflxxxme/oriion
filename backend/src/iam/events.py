"""CloudEvents emitters for the iam bounded context.

Matches contracts/iam/events.yaml 1:1 (ADR-024). Wave 0 transport: log
each envelope via structlog with cloudevent=True tag. Wave 1+ swap the
emit_envelope sink to Redis Streams XADD oriion:events:iam without
changing call-sites.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID, uuid4

import structlog

logger = structlog.get_logger(__name__)

_SOURCE = "oriion://contexts/iam"
_SPECVERSION = "1.0"
_DATACONTENTTYPE = "application/json"


def _envelope(event_type: str, data: dict[str, Any]) -> dict[str, Any]:
    return {
        "specversion": _SPECVERSION,
        "type": event_type,
        "source": _SOURCE,
        "id": str(uuid4()),
        "time": datetime.now(UTC).isoformat(),
        "datacontenttype": _DATACONTENTTYPE,
        "data": data,
    }


async def _emit(envelope: dict[str, Any]) -> None:
    """Wave 0 sink: structured log. Wave 1+ swap to Redis Streams."""
    logger.bind(cloudevent=True).info("iam.event.emitted", **envelope)


# ── user.* ────────────────────────────────────────────────────────────────


async def emit_user_registered(
    user_id: UUID,
    email: str,
    registered_at: datetime,
    registration_source: Literal[
        "password", "oauth_yandex", "oauth_google", "oauth_vk", "oauth_gitlab", "invite"
    ] = "password",
) -> None:
    await _emit(
        _envelope(
            "oriion.iam.user.registered.v1",
            {
                "user_id": str(user_id),
                "email": email,
                "registered_at": registered_at.isoformat(),
                "registration_source": registration_source,
            },
        )
    )


async def emit_email_verified(user_id: UUID, verified_at: datetime) -> None:
    await _emit(
        _envelope(
            "oriion.iam.user.email_verified.v1",
            {"user_id": str(user_id), "verified_at": verified_at.isoformat()},
        )
    )


async def emit_email_verification_requested(
    user_id: UUID,
    email: str,
    token_id: UUID,
    expires_at: datetime,
) -> None:
    """Plaintext token is NEVER in this event — only the row id."""
    await _emit(
        _envelope(
            "oriion.iam.user.email_verification_requested.v1",
            {
                "user_id": str(user_id),
                "email": email,
                "token_id": str(token_id),
                "expires_at": expires_at.isoformat(),
            },
        )
    )


async def emit_password_reset_requested(
    user_id: UUID,
    token_id: UUID,
    reset_chain_id: UUID,
    expires_at: datetime,
) -> None:
    await _emit(
        _envelope(
            "oriion.iam.user.password_reset_requested.v1",
            {
                "user_id": str(user_id),
                "token_id": str(token_id),
                "reset_chain_id": str(reset_chain_id),
                "expires_at": expires_at.isoformat(),
            },
        )
    )


async def emit_password_reset_completed(
    user_id: UUID,
    reset_chain_id: UUID,
    completed_at: datetime,
) -> None:
    await _emit(
        _envelope(
            "oriion.iam.user.password_reset_completed.v1",
            {
                "user_id": str(user_id),
                "reset_chain_id": str(reset_chain_id),
                "completed_at": completed_at.isoformat(),
            },
        )
    )


async def emit_consent_recorded(
    user_id: UUID,
    kind: Literal["pdn", "marketing", "tos"],
    version: str,
    action: Literal["granted", "revoked"],
    recorded_at: datetime,
) -> None:
    await _emit(
        _envelope(
            "oriion.iam.user.consent_recorded.v1",
            {
                "user_id": str(user_id),
                "kind": kind,
                "version": version,
                "action": action,
                "recorded_at": recorded_at.isoformat(),
            },
        )
    )


async def emit_user_deleted(
    user_id: UUID,
    deleted_at: datetime,
    retention_policy_days: int,
) -> None:
    await _emit(
        _envelope(
            "oriion.iam.user.deleted.v1",
            {
                "user_id": str(user_id),
                "deleted_at": deleted_at.isoformat(),
                "retention_policy_days": retention_policy_days,
            },
        )
    )


# ── session.* ─────────────────────────────────────────────────────────────


async def emit_session_created(
    session_id: UUID,
    user_id: UUID,
    expires_at: datetime,
    ip: str | None = None,
    user_agent_class: str | None = None,
) -> None:
    await _emit(
        _envelope(
            "oriion.iam.session.created.v1",
            {
                "session_id": str(session_id),
                "user_id": str(user_id),
                "ip": ip,
                "user_agent_class": user_agent_class,
                "expires_at": expires_at.isoformat(),
            },
        )
    )


async def emit_session_revoked(
    session_id: UUID,
    reason: Literal["user_action", "admin", "security_incident", "expired"],
) -> None:
    await _emit(
        _envelope(
            "oriion.iam.session.revoked.v1",
            {"session_id": str(session_id), "reason": reason},
        )
    )


# ── refresh + oauth ───────────────────────────────────────────────────────


async def emit_refresh_rotated(
    old_token_id: UUID,
    new_token_id: UUID,
    rotation_chain_id: UUID,
) -> None:
    await _emit(
        _envelope(
            "oriion.iam.refresh.rotated.v1",
            {
                "old_token_id": str(old_token_id),
                "new_token_id": str(new_token_id),
                "rotation_chain_id": str(rotation_chain_id),
            },
        )
    )


async def emit_oauth_linked(
    user_id: UUID,
    provider: Literal["yandex", "google", "vk", "gitlab"],
    provider_user_id: str,
) -> None:
    await _emit(
        _envelope(
            "oriion.iam.oauth.linked.v1",
            {
                "user_id": str(user_id),
                "provider": provider,
                "provider_user_id": provider_user_id,
            },
        )
    )
