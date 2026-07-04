"""Domain exceptions for the rbac bounded context.

Mirrors the multitenancy/billing exception shape (RFC 7807 problem-type):
each carries ``code`` / ``status_code`` / ``title`` so the app-level FastAPI
exception handler can render a uniform problem+json envelope.
"""

from __future__ import annotations


class RbacError(Exception):
    """Base domain exception for rbac."""

    code: str = "rbac.error"
    status_code: int = 500
    title: str = "RBAC error"

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail
        super().__init__(detail or self.title)


class PermissionDenied(RbacError):
    """The authenticated user lacks the required permission in the cell.

    403 (NOT 404): under Option A (flat visibility, ADR-014 §1) a Member
    legitimately *sees* the cell — they simply lack the right to perform the
    Owner-only action. Surfacing 403 (vs a 404 "hide existence") is correct
    because existence is not secret to a cell member.
    """

    code = "rbac.permission_denied"
    status_code = 403
    title = "You do not have permission to perform this action"
