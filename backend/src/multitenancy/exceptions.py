"""Domain exceptions for multitenancy.

Each exception carries:
  * code:        RFC 7807 problem-type identifier
  * status_code: HTTP status to surface via FastAPI exception handler
  * title:       human-readable summary
  * detail:      optional extra context
"""

from __future__ import annotations


class MultitenancyError(Exception):
    """Base domain exception for multitenancy."""

    code: str = "multitenancy.error"
    status_code: int = 500
    title: str = "Multitenancy error"

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail
        super().__init__(detail or self.title)


# ── 4xx: client errors ────────────────────────────────────────────────────


class WorkspaceNotFound(MultitenancyError):
    code = "multitenancy.workspace.not_found"
    status_code = 404
    title = "Workspace not found"


class WorkspaceSlugConflict(MultitenancyError):
    code = "multitenancy.workspace.slug_conflict"
    status_code = 409
    title = "Workspace slug already in use"


class CellNotFound(MultitenancyError):
    code = "multitenancy.cell.not_found"
    status_code = 404
    title = "Cell not found"


class CellSlugConflict(MultitenancyError):
    code = "multitenancy.cell.slug_conflict"
    status_code = 409
    title = "Cell slug already in use within this workspace"


class MemberAlreadyExists(MultitenancyError):
    code = "multitenancy.member.already_exists"
    status_code = 409
    title = "User is already a member of this cell"


class MemberNotFound(MultitenancyError):
    code = "multitenancy.member.not_found"
    status_code = 404
    title = "Cell member not found"


# ── 5xx: server / infra errors ────────────────────────────────────────────


class CellProvisioningError(MultitenancyError):
    """Raised when multitenancy.provision_cell_schema() fails or returns
    an unexpected schema name. Bubble through as 500 — operators investigate."""

    code = "multitenancy.cell.provisioning_failed"
    status_code = 500
    title = "Cell schema provisioning failed"
