"""Unit: EmailSender impls."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from unittest.mock import AsyncMock, patch

import pytest
from src.iam.services.email_service import (
    ConsoleEmailSender,
    InMemoryEmailSender,
    NoOpEmailSender,
    YandexSmtpEmailSender,
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
async def test_inmemory_captures_magic_link() -> None:
    s = InMemoryEmailSender()
    await s.send_magic_link_email("m@x.dev", "tok", datetime.now(UTC))
    assert s.last().kind == "magic_link"
    assert s.last().to == "m@x.dev"


@pytest.mark.asyncio
async def test_console_does_not_raise() -> None:
    s = ConsoleEmailSender()
    await s.send_verification_email("a@b.dev", "tok", datetime.now(UTC))
    await s.send_password_reset_email("a@b.dev", "tok", datetime.now(UTC))
    await s.send_magic_link_email("a@b.dev", "tok", datetime.now(UTC))


@pytest.mark.asyncio
async def test_noop_does_not_raise() -> None:
    s = NoOpEmailSender()
    await s.send_verification_email("a@b.dev", "tok", datetime.now(UTC))
    await s.send_password_reset_email("a@b.dev", "tok", datetime.now(UTC))
    await s.send_magic_link_email("a@b.dev", "tok", datetime.now(UTC))


# ── Phase 01.8 — YandexSmtpEmailSender (transport-mocked, NO live network) ───


def _implicit_tls_sender(**overrides: object) -> YandexSmtpEmailSender:
    kwargs: dict[str, object] = {
        "host": "smtp.yandex.ru",
        "port": 465,
        "username": "no-reply@profiki.online",
        "password": "app-pass-secret",
        "sender": "no-reply@profiki.online",
        "use_tls": True,
        "timeout": 30.0,
        "url_base": "",
    }
    kwargs.update(overrides)
    return YandexSmtpEmailSender(**kwargs)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_smtp_verification_builds_message_and_calls_transport() -> None:
    sender = _implicit_tls_sender()
    exp = datetime.now(UTC) + timedelta(hours=1)
    with patch("src.iam.services.email_service.aiosmtplib.send", AsyncMock()) as mock_send:
        await sender.send_verification_email("user@example.com", "VTOKEN123", exp)

    assert mock_send.await_count == 1
    args, kwargs = mock_send.await_args
    # host / port / TLS mode selected correctly (implicit TLS on 465)
    assert kwargs["hostname"] == "smtp.yandex.ru"
    assert kwargs["port"] == 465
    assert kwargs["use_tls"] is True
    assert kwargs["start_tls"] is False
    assert kwargs["timeout"] == 30.0
    # auth called with configured creds
    assert kwargs["username"] == "no-reply@profiki.online"
    assert kwargs["password"] == "app-pass-secret"
    # MIME message: correct recipient / subject / token-in-body
    message = args[0]
    assert isinstance(message, EmailMessage)
    assert message["To"] == "user@example.com"
    assert message["From"] == "no-reply@profiki.online"
    assert "Подтвердите" in str(message["Subject"])
    body = message.get_content()
    assert "VTOKEN123" in body
    assert "/auth/verify-email" in body


@pytest.mark.asyncio
async def test_smtp_password_reset_builds_message() -> None:
    sender = _implicit_tls_sender()
    exp = datetime.now(UTC) + timedelta(hours=1)
    with patch("src.iam.services.email_service.aiosmtplib.send", AsyncMock()) as mock_send:
        await sender.send_password_reset_email("reset@example.com", "RTOKEN999", exp)

    args, kwargs = mock_send.await_args
    message = args[0]
    assert message["To"] == "reset@example.com"
    assert "пароля" in str(message["Subject"])
    body = message.get_content()
    assert "RTOKEN999" in body
    assert "/auth/reset-password" in body


@pytest.mark.asyncio
async def test_smtp_magic_link_builds_message() -> None:
    sender = _implicit_tls_sender()
    exp = datetime.now(UTC) + timedelta(minutes=15)
    with patch("src.iam.services.email_service.aiosmtplib.send", AsyncMock()) as mock_send:
        await sender.send_magic_link_email("magic@example.com", "MLTOKEN42", exp)

    args, _ = mock_send.await_args
    message = args[0]
    assert message["To"] == "magic@example.com"
    assert "ссылке" in str(message["Subject"])
    body = message.get_content()
    assert "MLTOKEN42" in body
    assert "/auth/magic-link/consume" in body


@pytest.mark.asyncio
async def test_smtp_starttls_mode_uses_start_tls_not_implicit() -> None:
    # port 587 STARTTLS branch — implicit TLS off, STARTTLS upgrade required
    sender = _implicit_tls_sender(port=587, use_tls=False)
    with patch("src.iam.services.email_service.aiosmtplib.send", AsyncMock()) as mock_send:
        await sender.send_verification_email("u@example.com", "tok", datetime.now(UTC))

    _, kwargs = mock_send.await_args
    assert kwargs["port"] == 587
    assert kwargs["use_tls"] is False
    assert kwargs["start_tls"] is True  # forces upgrade before AUTH (no cleartext auth)


@pytest.mark.asyncio
async def test_smtp_url_base_produces_clickable_link() -> None:
    sender = _implicit_tls_sender(url_base="https://app.profiki.online/")
    with patch("src.iam.services.email_service.aiosmtplib.send", AsyncMock()) as mock_send:
        await sender.send_verification_email("u@example.com", "LINKTOK", datetime.now(UTC))

    message = mock_send.await_args.args[0]
    body = message.get_content()
    assert "https://app.profiki.online/auth/verify-email?token=LINKTOK" in body


@pytest.mark.asyncio
async def test_smtp_send_failure_propagates() -> None:
    # A transport error MUST surface — a verification email must never look
    # "sent" when it wasn't (SOUND invariant).
    sender = _implicit_tls_sender()
    boom = AsyncMock(side_effect=RuntimeError("SMTP connect failed"))
    with (
        patch("src.iam.services.email_service.aiosmtplib.send", boom),
        pytest.raises(RuntimeError),
    ):
        await sender.send_verification_email("u@example.com", "tok", datetime.now(UTC))


@pytest.mark.asyncio
async def test_smtp_token_not_logged(caplog: pytest.LogCaptureFixture) -> None:
    # The plaintext token must NEVER appear in logs (prod invariant 7+8).
    sender = _implicit_tls_sender()
    with (
        patch("src.iam.services.email_service.aiosmtplib.send", AsyncMock()),
        caplog.at_level("DEBUG"),
    ):
        await sender.send_verification_email("u@example.com", "SECRET_TOKEN_XYZ", datetime.now(UTC))
    assert "SECRET_TOKEN_XYZ" not in caplog.text


@pytest.mark.live
@pytest.mark.asyncio
async def test_smtp_live_send_smoke() -> None:
    """Live-send smoke test — DEFERRED gate (Phase 01.8, ADR-007).

    Skipped unless SMTP_LIVE_TEST_TO + SMTP creds are present in env. This is
    the one command that validates real delivery once creds land in the
    canonical .env. Run with:

        SMTP_LIVE_TEST_TO=you@example.com SMTP_USER=... SMTP_PASSWORD=... \\
        uv run pytest tests/iam/unit/test_email_service.py -m live

    Required env keys: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD,
    SMTP_FROM (optional), SMTP_USE_TLS (optional, default true), and
    SMTP_LIVE_TEST_TO (the mailbox to deliver to).
    """
    to = os.environ.get("SMTP_LIVE_TEST_TO", "").strip()
    user = os.environ.get("SMTP_USER", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "").strip()
    if not (to and user and password):
        pytest.skip("SMTP_LIVE_TEST_TO + SMTP_USER + SMTP_PASSWORD required for live send")

    sender = YandexSmtpEmailSender(
        host=os.environ.get("SMTP_HOST", "smtp.yandex.ru"),
        port=int(os.environ.get("SMTP_PORT", "465")),
        username=user,
        password=password,
        sender=os.environ.get("SMTP_FROM", "") or user,
        use_tls=os.environ.get("SMTP_USE_TLS", "true").lower() != "false",
    )
    await sender.send_verification_email(
        to, "live-smoke-token", datetime.now(UTC) + timedelta(hours=1)
    )
