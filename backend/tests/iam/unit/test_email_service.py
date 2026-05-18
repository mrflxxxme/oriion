"""Unit: EmailSender impls."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from src.iam.services.email_service import (
    ConsoleEmailSender,
    InMemoryEmailSender,
    NoOpEmailSender,
)


@pytest.mark.asyncio
async def test_inmemory_captures_verification() -> None:
    s = InMemoryEmailSender()
    await s.send_verification_email("a@b.dev", "tok", datetime.now(UTC))
    assert len(s.outbox) == 1
    assert s.last().to == "a@b.dev"
    assert s.last().kind == "verification"
    s.clear()
    assert s.outbox == []


@pytest.mark.asyncio
async def test_inmemory_captures_password_reset() -> None:
    s = InMemoryEmailSender()
    await s.send_password_reset_email("u@x.dev", "tok", datetime.now(UTC))
    assert s.last().kind == "password_reset"


@pytest.mark.asyncio
async def test_console_does_not_raise() -> None:
    s = ConsoleEmailSender()
    await s.send_verification_email("a@b.dev", "tok", datetime.now(UTC))
    await s.send_password_reset_email("a@b.dev", "tok", datetime.now(UTC))


@pytest.mark.asyncio
async def test_noop_does_not_raise() -> None:
    s = NoOpEmailSender()
    await s.send_verification_email("a@b.dev", "tok", datetime.now(UTC))
    await s.send_password_reset_email("a@b.dev", "tok", datetime.now(UTC))
