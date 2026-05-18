"""Stub for multitenancy.provision_initial_workspace.

Signature is contract-locked per
.planning/_session-context/2026-05-17-architect-pr-3-way-parallel.md §Stub 1.

Real impl lands from Phase 00.3 at
backend/src/multitenancy/services/workspace_service.py with the same
signature; integration phase 00.2.5 swaps the import.

Determinism: workspace_id and cell_id are derived via uuid5(NAMESPACE_OID, ...)
from the user_id so smoke-tests against the stub get stable IDs.
"""

from __future__ import annotations

from uuid import NAMESPACE_OID, UUID, uuid5

import structlog
from pydantic import BaseModel

logger = structlog.get_logger(__name__)


class WorkspaceProvisionResult(BaseModel):
    """Returned by provision_initial_workspace.

    Matches the shape that the real impl in 00.3 will return; 00.2.5
    integration swap is a pure import replacement.
    """

    workspace_id: UUID
    cell_id: UUID


async def provision_initial_workspace(user_id: UUID) -> WorkspaceProvisionResult:
    """Stub: returns deterministic IDs and emits a WARNING.

    Production behaviour (Phase 00.3):
        - INSERT into multitenancy.workspaces
        - INSERT into multitenancy.cells
        - INSERT into multitenancy.workspace_members with role='owner'
        - Emit oriion.multitenancy.workspace.created.v1
    """
    workspace_id = uuid5(NAMESPACE_OID, f"workspace:{user_id}")
    cell_id = uuid5(NAMESPACE_OID, f"cell:{user_id}")
    logger.warning(
        "STUB multitenancy.provision_initial_workspace — replace via 00.3 integration",
        user_id=str(user_id),
        workspace_id=str(workspace_id),
        cell_id=str(cell_id),
    )
    return WorkspaceProvisionResult(workspace_id=workspace_id, cell_id=cell_id)
