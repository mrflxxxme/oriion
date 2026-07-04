"""Unit: MagicLinkService — request (anti-enum) + consume (single-use)."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from src.iam.exceptions import RateLimitExceeded, TokenNotFound
from src.iam.schemas import TokenPair
from src.iam.services.email_service import InMemoryEmailSender
from src.iam.services.magic_link_service import MagicLinkService
from src.iam.services.rate_limit_service import RateLimitService


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _build(
    *,
    rate_limit_service: RateLimitService,
    email_sender: InMemoryEmailSender,
    user_repo: AsyncMock | None = None,
    magic_link_repo: AsyncMock | None = None,
    issue_token_pair: AsyncMock | None = None,
) -> tuple[MagicLinkService, dict[str, AsyncMock]]:
    user_repo = user_repo or AsyncMock()
    magic_link_repo = magic_link_repo or AsyncMock()
    issue_token_pair = issue_token_pair or AsyncMock(
        return_value=TokenPair(access_token="a", refresh_token="r", expires_in=900)
    )
    svc = MagicLinkService(
        session=AsyncMock(),
        user_repo=user_repo,
        magic_link_repo=magic_link_repo,
        rate_limit_service=rate_limit_service,
        email_sender=email_sender,
        issue_token_pair=issue_token_pair,
    )
    return svc, {"user": user_repo, "magic": magic_link_repo, "issue": issue_token_pair}


# ── request ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_request_sends_link_for_existing_user(
    rate_limit_service: RateLimitService, email_sender: InMemoryEmailSender
) -> None:
    user_repo = AsyncMock()
    user_repo.find_by_email.return_value = SimpleNamespace(id=uuid4(), email="user@x.dev")
    magic_repo = AsyncMock()
    svc, _ = _build(
        rate_limit_service=rate_limit_service,
        email_sender=email_sender,
        user_repo=user_repo,
        magic_link_repo=magic_repo,
    )

    await svc.request("user@x.dev", ip="1.2.3.4", user_agent="pytest")

    # Prior unused links revoked, new token created, email sent (hashed at rest).
    magic_repo.revoke_unused_for_user.assert_awaited_once()
    magic_repo.create.assert_awaited_once()
    assert len(email_sender.outbox) == 1
    rec = email_sender.outbox[0]
    assert rec.kind == "magic_link"
    assert rec.to == "user@x.dev"
    # The stored hash is of the emailed plaintext (plaintext never persisted).
    _, kwargs = magic_repo.create.call_args
    assert kwargs["token_hash"] == _sha256(rec.token)


@pytest.mark.asyncio
async def test_request_is_silent_for_unknown_email_anti_enum(
    rate_limit_service: RateLimitService, email_sender: InMemoryEmailSender
) -> None:
    user_repo = AsyncMock()
    user_repo.find_by_email.return_value = None
    magic_repo = AsyncMock()
    svc, _ = _build(
        rate_limit_service=rate_limit_service,
        email_sender=email_sender,
        user_repo=user_repo,
        magic_link_repo=magic_repo,
    )

    await svc.request("ghost@x.dev", ip="1.2.3.4", user_agent="pytest")

    # No token, no email — indistinguishable from the existing-user path to a
    # caller (both return None).
    magic_repo.create.assert_not_awaited()
    assert len(email_sender.outbox) == 0


@pytest.mark.asyncio
async def test_request_rate_limited(
    rate_limit_service: RateLimitService, email_sender: InMemoryEmailSender
) -> None:
    svc, _ = _build(rate_limit_service=rate_limit_service, email_sender=email_sender)
    # magic_link policy = 3 / 15 min. 4th call from same ip+email → 429.
    for _ in range(3):
        await svc.request("user@x.dev", ip="9.9.9.9", user_agent="pytest")
    with pytest.raises(RateLimitExceeded):
        await svc.request("user@x.dev", ip="9.9.9.9", user_agent="pytest")


# ── consume ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_consume_valid_token_issues_pair_and_marks_used(
    rate_limit_service: RateLimitService, email_sender: InMemoryEmailSender
) -> None:
    token_id = uuid4()
    user_id = uuid4()
    magic_repo = AsyncMock()
    magic_repo.find_active_by_hash.return_value = SimpleNamespace(
        id=token_id, user_id=user_id, expires_at=datetime.now(UTC) + timedelta(minutes=5)
    )
    issue = AsyncMock(
        return_value=TokenPair(access_token="acc", refresh_token="ref", expires_in=900)
    )
    svc, _ = _build(
        rate_limit_service=rate_limit_service,
        email_sender=email_sender,
        magic_link_repo=magic_repo,
        issue_token_pair=issue,
    )

    pair = await svc.consume("plaintext-token", ip="1.2.3.4", user_agent="pytest")

    assert pair.access_token == "acc"
    # Single-use: mark_used called BEFORE issuing so a race can't double-mint.
    magic_repo.mark_used.assert_awaited_once_with(token_id)
    issue.assert_awaited_once()
    _, kwargs = issue.call_args
    assert kwargs["user_id"] == user_id


@pytest.mark.asyncio
async def test_consume_unknown_token_rejected(
    rate_limit_service: RateLimitService, email_sender: InMemoryEmailSender
) -> None:
    magic_repo = AsyncMock()
    magic_repo.find_active_by_hash.return_value = None
    svc, _ = _build(
        rate_limit_service=rate_limit_service,
        email_sender=email_sender,
        magic_link_repo=magic_repo,
    )

    with pytest.raises(TokenNotFound):
        await svc.consume("nope", ip=None, user_agent=None)


@pytest.mark.asyncio
async def test_consume_expired_token_rejected(
    rate_limit_service: RateLimitService, email_sender: InMemoryEmailSender
) -> None:
    magic_repo = AsyncMock()
    magic_repo.find_active_by_hash.return_value = SimpleNamespace(
        id=uuid4(), user_id=uuid4(), expires_at=datetime.now(UTC) - timedelta(minutes=1)
    )
    svc, mocks = _build(
        rate_limit_service=rate_limit_service,
        email_sender=email_sender,
        magic_link_repo=magic_repo,
    )

    with pytest.raises(TokenNotFound):
        await svc.consume("expired", ip=None, user_agent=None)
    # Expired → no token issued.
    mocks["issue"].assert_not_awaited()
