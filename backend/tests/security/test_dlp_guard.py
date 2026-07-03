"""Unit tests for the DLP output guard — A3 hard-block (ADR-039).

Uses a fake AuditSink so the full block path (scan -> audit -> raise) is proven
with no DB. The key security assertion: neither the audit call nor the raised
exception carries the raw PII value — only category labels.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

import pytest
from src.security.exceptions import DlpViolation
from src.security.services.dlp import DlpGuard

VALID_INN10 = "7830002293"


@dataclass
class FakeAuditSink:
    calls: list[dict[str, object]] = field(default_factory=list)

    async def record_dlp_block(
        self,
        *,
        task_id: UUID,
        cell_id: UUID | None,
        workspace_id: UUID | None,
        categories: tuple[str, ...],
        finding_count: int,
    ) -> None:
        self.calls.append(
            {
                "task_id": task_id,
                "cell_id": cell_id,
                "workspace_id": workspace_id,
                "categories": categories,
                "finding_count": finding_count,
            }
        )


def _ctx() -> dict[str, UUID]:
    return {"task_id": uuid4(), "cell_id": uuid4(), "workspace_id": uuid4()}


class TestCleanDeliverable:
    async def test_no_pii_no_audit_no_raise(self) -> None:
        sink = FakeAuditSink()
        guard = DlpGuard(audit=sink)
        await guard.screen("Маркетинговый бриф без ПДн.", **_ctx())
        assert sink.calls == []


class TestBlockOnPii:
    async def test_pii_audits_and_raises(self) -> None:
        sink = FakeAuditSink()
        guard = DlpGuard(audit=sink)
        ctx = _ctx()
        with pytest.raises(DlpViolation) as exc_info:
            await guard.screen(f"ИНН клиента {VALID_INN10}", **ctx)
        # audited exactly once with the category label + count, scoped to the cell.
        assert len(sink.calls) == 1
        call = sink.calls[0]
        assert call["categories"] == ("inn",)
        assert call["finding_count"] == 1
        assert call["cell_id"] == ctx["cell_id"]
        assert call["task_id"] == ctx["task_id"]
        # exception carries the category, and the error code the runtime keys on.
        assert exc_info.value.categories == ("inn",)
        assert exc_info.value.code == "security.dlp.blocked"

    async def test_raw_value_never_leaks(self) -> None:
        sink = FakeAuditSink()
        guard = DlpGuard(audit=sink)
        with pytest.raises(DlpViolation) as exc_info:
            await guard.screen(f"ИНН {VALID_INN10}", **_ctx())
        # SECURITY: the raw INN must not appear in the exception (echoed to SSE)
        # nor in the audit payload (persisted).
        assert VALID_INN10 not in str(exc_info.value)
        assert all(VALID_INN10 not in str(v) for v in sink.calls[0].values())

    async def test_multiple_categories_deduped_sorted(self) -> None:
        sink = FakeAuditSink()
        guard = DlpGuard(audit=sink)
        text = f"ИНН {VALID_INN10}, e-mail a@b.co, тел +79161234567"
        with pytest.raises(DlpViolation) as exc_info:
            await guard.screen(text, **_ctx())
        cats = exc_info.value.categories
        assert set(cats) == {"inn", "email", "phone"}
        assert list(cats) == sorted(cats)
