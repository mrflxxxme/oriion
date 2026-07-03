"""Output-DLP guardrail wiring (Phase 01.6, ADR-039).

The worker (``runtime.queue.actor``) builds the real output-DLP screen here and
passes it to ``execute_agent_task`` (the orchestrator default is ``None`` ⇒
no-op, mirroring ``memory_extraction``/``quota_admission``). Gated by
``Settings.security_dlp_enabled`` — off in Wave-1 (no outward PII surface yet;
ADR-039 §4), so the worker leaves the seam ``None`` unless the flag is on.

``EmitAuditSink`` is the real ``AuditSink`` adapter: it wraps
``audit.emit_audit_event`` with a fixed synthetic system actor. SECURITY: only
category labels + a count reach the audit row — never the raw PII value.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.audit.services.audit_service import emit_audit_event
from src.runtime.orchestrator import OutputDlpScreen
from src.security.ports import AuditSink
from src.security.services.dlp import DlpGuard

# Fixed synthetic actor for guardrail-originated audit rows (the block is a
# system action, not a user action). Stable so audit queries can filter on it.
GUARDRAIL_ACTOR_ID = UUID("5ec00000-0000-0000-0000-000000000d19")

DLP_BLOCK_ACTION = "security.dlp.blocked"


class EmitAuditSink:
    """Real ``AuditSink`` — INSERTs a DLP-block row via ``emit_audit_event``.

    Writes on the caller's session (no commit): on the failure path the actor
    commits both the ``task.failed`` status and this row. SECURITY: the payload
    carries category labels + a count only, never the matched PII value.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record_dlp_block(
        self,
        *,
        task_id: UUID,
        cell_id: UUID | None,
        workspace_id: UUID | None,
        categories: tuple[str, ...],
        finding_count: int,
    ) -> None:
        await emit_audit_event(
            actor_type="system",
            actor_id=GUARDRAIL_ACTOR_ID,
            action=DLP_BLOCK_ACTION,
            resource_type="task",
            resource_id=task_id,
            payload={"categories": list(categories), "finding_count": finding_count},
            session=self._session,
            workspace_id=workspace_id,
            cell_id=cell_id,
        )


def build_output_dlp_screen(
    *,
    session: AsyncSession,
    task_id: UUID,
    cell_id: UUID,
    workspace_id: UUID,
    audit: AuditSink | None = None,
) -> OutputDlpScreen:
    """Build the orchestrator's output-DLP screen closure (worker-wired).

    ``audit`` defaults to the real ``EmitAuditSink``; unit tests inject a fake.
    """
    guard = DlpGuard(audit=audit or EmitAuditSink(session))

    async def _screen(deliverable: str) -> None:
        await guard.screen(deliverable, task_id=task_id, cell_id=cell_id, workspace_id=workspace_id)

    return _screen


__all__ = [
    "DLP_BLOCK_ACTION",
    "GUARDRAIL_ACTOR_ID",
    "EmitAuditSink",
    "build_output_dlp_screen",
]
