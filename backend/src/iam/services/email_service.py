"""EmailSender Protocol + 3 implementations.

Wave 0 stack:
  ConsoleEmailSender  — dev default; prints to structured log so the founder
                        can copy the plaintext token from terminal.
  NoOpEmailSender     — silent placeholder used in prod until Yandex SMTP
                        ships in Wave 1.
  InMemoryEmailSender — test fixture only; captures sent emails in a list
                        so integration tests can assert on subject + body.

Plaintext tokens travel only via email (invariants 7+8). The sender NEVER
persists them; only the SHA-256 hex hash lives in the DB.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Protocol

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
