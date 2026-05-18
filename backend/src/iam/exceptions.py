"""Domain exceptions for iam.

Each exception carries:
  * code:        RFC 7807 problem-type identifier (e.g. iam.auth.invalid_credentials)
  * status_code: HTTP status to surface via FastAPI exception handler
  * title:       human-readable summary
  * detail:      optional extra context

Exception handler in routers/auth.py maps these into application/problem+json
responses per OpenAPI contract.
"""

from __future__ import annotations


class IamError(Exception):
    """Base domain exception for iam."""

    code: str = "iam.error"
    status_code: int = 500
    title: str = "IAM error"

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail
        super().__init__(detail or self.title)


# ── 4xx: client errors ────────────────────────────────────────────────────


class InvalidCredentials(IamError):
    code = "iam.auth.invalid_credentials"
    status_code = 401
    title = "Invalid credentials"


class EmailAlreadyRegistered(IamError):
    code = "iam.auth.email_already_registered"
    status_code = 409
    title = "Email already registered"


class ConsentMissing(IamError):
    code = "iam.consent.pdn_missing"
    status_code = 422
    title = "FZ-152 personal-data consent is required to register"


class TokenExpired(IamError):
    code = "iam.auth.token_expired"
    status_code = 401
    title = "Token expired"


class TokenInvalid(IamError):
    code = "iam.auth.token_invalid"
    status_code = 401
    title = "Token invalid"


class TokenRevoked(IamError):
    code = "iam.auth.token_revoked"
    status_code = 401
    title = "Token revoked"


class TokenRotationError(IamError):
    """OWASP refresh-rotation reuse-detection — entire chain revoked."""

    code = "iam.auth.refresh_rotation_violation"
    status_code = 401
    title = "Refresh token rotation violation"


class TokenNotFound(IamError):
    code = "iam.auth.token_not_found"
    status_code = 410
    title = "Token expired, already used, or never existed"


class EmailNotVerified(IamError):
    code = "iam.auth.email_not_verified"
    status_code = 403
    title = "Email not verified"


class RateLimitExceeded(IamError):
    code = "iam.auth.rate_limit_exceeded"
    status_code = 429
    title = "Rate limit exceeded"

    def __init__(self, retry_after: int, detail: str | None = None) -> None:
        super().__init__(detail)
        self.retry_after = retry_after


class WeakPassword(IamError):
    code = "iam.auth.weak_password"
    status_code = 422
    title = "Password does not meet policy"


class UserNotFound(IamError):
    code = "iam.user.not_found"
    status_code = 404
    title = "User not found"
