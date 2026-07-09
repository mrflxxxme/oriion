# ruff: noqa: RUF001, RUF002, RUF003 — realistic RU deliverable content by domain
"""Success-path activation check for the output-DLP screen (AC-01.9a.5).

With the flags ON, a realistic benign agent deliverable must flow through the
same ``_dlp_screen_text`` → ``DlpGuard.screen`` path the worker uses WITHOUT
raising, while a deliverable that carries a contextual ИНН MUST raise
``DlpViolation``. This is the "DLP does not break task-success, but does block
real PDn" integration the flag-flip must not regress.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel
from src.runtime.orchestrator import _dlp_screen_text
from src.security.exceptions import DlpViolation
from src.security.services.dlp import DlpGuard

VALID_INN10 = "7830002293"


class _Deliverable(BaseModel):
    """Stand-in for an agent's final structured output (outward fields)."""

    summary: str
    assumptions: str = ""


@dataclass
class _FakeAuditSink:
    calls: list[tuple[str, ...]] = field(default_factory=list)

    async def record_dlp_block(
        self,
        *,
        task_id: UUID,
        cell_id: UUID | None,
        workspace_id: UUID | None,
        categories: tuple[str, ...],
        finding_count: int,
    ) -> None:
        self.calls.append(categories)


def _ctx() -> dict[str, Any]:
    return {"task_id": uuid4(), "cell_id": uuid4(), "workspace_id": uuid4()}


_BENIGN = _Deliverable(
    summary=(
        "Маркетинговый бриф: целевая аудитория — SMB в сфере услуг, тон дружелюбный. "
        "Рекомендуемые каналы: Telegram и email-рассылка. Бюджет на квартал — 150 тыс. "
        "Заказ №1420 согласован, срок запуска — 2026 год."
    ),
    assumptions="Кампания рассчитана на 12 недель без привлечения подрядчиков.",
)


async def test_benign_deliverable_passes_without_raising() -> None:
    guard = DlpGuard(audit=_FakeAuditSink())
    await guard.screen(_dlp_screen_text(_BENIGN), **_ctx())  # must not raise


async def test_contextual_inn_deliverable_is_blocked() -> None:
    sink = _FakeAuditSink()
    guard = DlpGuard(audit=sink)
    pii_output = _Deliverable(
        summary="Готовый оффер для клиента.",
        assumptions=f"Контрагент, ИНН {VALID_INN10}, включён в договор.",
    )
    with pytest.raises(DlpViolation) as exc_info:
        await guard.screen(_dlp_screen_text(pii_output), **_ctx())
    assert exc_info.value.categories == ("inn",)
    assert sink.calls == [("inn",)]
    # SECURITY: the raw INN never rides the exception (it is echoed to SSE).
    assert VALID_INN10 not in str(exc_info.value)
