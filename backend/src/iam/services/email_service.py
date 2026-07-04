"""EmailSender Protocol + implementations.

Wave 0 stack:
  ConsoleEmailSender  — dev default; prints to structured log so the founder
                        can copy the plaintext token from terminal.
  NoOpEmailSender     — silent placeholder used in prod until Yandex SMTP
                        ships in Wave 1.
  InMemoryEmailSender — test fixture only; captures sent emails in a list
                        so integration tests can assert on subject + body.

Wave 1 (Phase 01.8):
  YandexSmtpEmailSender — real transactional SMTP over Yandex 360, used in prod
                          ONLY when SMTP creds are configured (else NoOp). Live
                          send is a deferred gate — it validates when creds land
                          in the canonical .env (they are NOT present now).

Plaintext tokens travel only via email (invariants 7+8). The sender NEVER
persists them; only the SHA-256 hex hash lives in the DB. In prod the token is
NEVER logged at INFO — YandexSmtpEmailSender logs recipient + kind only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from email.message import EmailMessage
from typing import Literal, Protocol

import aiosmtplib
import structlog

logger = structlog.get_logger(__name__)


EmailKind = Literal["verification", "password_reset"]


@dataclass(frozen=True, slots=True)
class EmailRecord:
    """A single send attempt — used by tests + dev outbox."""

    to: str
    kind: EmailKind
    token: str
    expires_at: datetime


class EmailSender(Protocol):
    async def send_verification_email(self, to: str, token: str, expires_at: datetime) -> None: ...

    async def send_password_reset_email(
        self, to: str, token: str, expires_at: datetime
    ) -> None: ...


class ConsoleEmailSender:
    """Dev impl — logs the token to stdout via structlog.

    The plaintext token appears in the structured log so the founder can
    grep/copy it for smoke-testing. Never use in prod.
    """

    async def send_verification_email(self, to: str, token: str, expires_at: datetime) -> None:
        logger.info(
            "[EMAIL.VERIFY] dev console email — copy token to /auth/verify-email",
            to=to,
            token=token,
            expires_at=expires_at.isoformat(),
        )

    async def send_password_reset_email(self, to: str, token: str, expires_at: datetime) -> None:
        logger.info(
            "[EMAIL.RESET] dev console email — copy token to /auth/reset-password",
            to=to,
            token=token,
            expires_at=expires_at.isoformat(),
        )


class NoOpEmailSender:
    """Prod placeholder until Yandex 360 SMTP integration (Wave 1)."""

    async def send_verification_email(self, to: str, token: str, expires_at: datetime) -> None:
        logger.warning(
            "NoOpEmailSender — verification email NOT sent (Wave 1 SMTP missing)",
            to=to,
        )

    async def send_password_reset_email(self, to: str, token: str, expires_at: datetime) -> None:
        logger.warning(
            "NoOpEmailSender — password reset email NOT sent (Wave 1 SMTP missing)",
            to=to,
        )


@dataclass
class InMemoryEmailSender:
    """Test fixture — captures sent emails in `outbox` for assertions."""

    outbox: list[EmailRecord] = field(default_factory=list)

    async def send_verification_email(self, to: str, token: str, expires_at: datetime) -> None:
        self.outbox.append(
            EmailRecord(to=to, kind="verification", token=token, expires_at=expires_at)
        )

    async def send_password_reset_email(self, to: str, token: str, expires_at: datetime) -> None:
        self.outbox.append(
            EmailRecord(to=to, kind="password_reset", token=token, expires_at=expires_at)
        )

    def last(self) -> EmailRecord:
        return self.outbox[-1]

    def clear(self) -> None:
        self.outbox.clear()


# ── Phase 01.8 — real Yandex 360 SMTP sender ────────────────────────────────

_VERIFY_SUBJECT = "Подтвердите email — TEAMLY"
_RESET_SUBJECT = "Сброс пароля — TEAMLY"


class YandexSmtpEmailSender:
    """Real transactional email over Yandex 360 SMTP (Phase 01.8, ADR-007).

    Sends verification / password-reset mail via ``aiosmtplib`` with TLS
    enforced. Two transport modes, driven by ``use_tls``:

      * ``use_tls=True``  → implicit TLS (SSL-on-connect), Yandex port 465.
      * ``use_tls=False`` → STARTTLS upgrade on a cleartext port (587).
        ``start_tls=True`` REQUIRES the upgrade to succeed before AUTH, so
        credentials never travel over cleartext. Certificate verification is
        left at the aiosmtplib/ssl default (enabled) — never disabled.

    Invariants preserved:
      * The plaintext token travels ONLY in the email body; it is NEVER logged
        (only ``to`` + ``kind`` are logged) and NEVER persisted by the sender.
      * A send failure PROPAGATES (aiosmtplib raises) — the caller's task fails
        rather than a verification email looking "sent" when it wasn't.
    """

    def __init__(
        self,
        *,
        host: str,
        port: int,
        username: str,
        password: str,
        sender: str,
        use_tls: bool,
        timeout: float = 30.0,
        url_base: str = "",
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._sender = sender
        self._use_tls = use_tls
        self._timeout = timeout
        self._url_base = url_base.rstrip("/")

    # ── link / body composition ─────────────────────────────────────────
    def _action_ref(self, path: str, token: str) -> str:
        """Full clickable link when a url_base is set, else the API path.

        Matches ConsoleEmailSender semantics: without a public base URL the
        body carries the bare token + the endpoint path the user posts it to.
        """
        if self._url_base:
            return f"{self._url_base}{path}?token={token}"
        return f"{path} (token: {token})"

    def _build_message(self, *, to: str, subject: str, body: str) -> EmailMessage:
        message = EmailMessage()
        message["From"] = self._sender
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)
        return message

    async def _send(self, message: EmailMessage, *, to: str, kind: EmailKind) -> None:
        # aiosmtplib.send handles connect → (STARTTLS|implicit TLS) → AUTH →
        # DATA → QUIT. `start_tls=True` forces the STARTTLS upgrade to succeed
        # before AUTH on the cleartext-port path; `use_tls=True` opens the
        # socket already wrapped in SSL. Exactly one is enabled.
        await aiosmtplib.send(
            message,
            hostname=self._host,
            port=self._port,
            username=self._username,
            password=self._password,
            use_tls=self._use_tls,
            start_tls=not self._use_tls,
            timeout=self._timeout,
        )
        # Token deliberately absent from this log line (prod invariant 7+8).
        logger.info("smtp email sent", to=to, kind=kind, host=self._host)

    async def send_verification_email(self, to: str, token: str, expires_at: datetime) -> None:
        ref = self._action_ref("/auth/verify-email", token)
        body = (
            "Здравствуйте!\n\n"
            "Подтвердите ваш email для доступа к TEAMLY.\n\n"
            f"{ref}\n\n"
            f"Ссылка действительна до {expires_at.isoformat()}.\n\n"
            "Если вы не создавали аккаунт, просто проигнорируйте это письмо.\n"
        )
        message = self._build_message(to=to, subject=_VERIFY_SUBJECT, body=body)
        await self._send(message, to=to, kind="verification")

    async def send_password_reset_email(self, to: str, token: str, expires_at: datetime) -> None:
        ref = self._action_ref("/auth/reset-password", token)
        body = (
            "Здравствуйте!\n\n"
            "Мы получили запрос на сброс пароля для вашего аккаунта TEAMLY.\n\n"
            f"{ref}\n\n"
            f"Ссылка действительна до {expires_at.isoformat()}.\n\n"
            "Если вы не запрашивали сброс, проигнорируйте это письмо — "
            "пароль останется прежним.\n"
        )
        message = self._build_message(to=to, subject=_RESET_SUBJECT, body=body)
        await self._send(message, to=to, kind="password_reset")
