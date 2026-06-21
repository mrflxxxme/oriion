"""StrategicContext — the Master → Coordinator strategic brief (ADR-029).

Wave 1 Master-Agent layer (AC-W1-3). For **vertical** templates a
``MasterAgent`` (vertical "CEO": domain lens + strategic planning) sits above
the existing ``Coordinator`` (operational "COO"). The Master interprets the
user message through a domain lens, forms a strategic objective, and hands the
Coordinator a ``StrategicContext`` alongside the objective prompt.

This type is the **optional** carrier of that brief. It is threaded through
``CoordinatorDeps.strategic_context`` (default ``None``): when absent the
Coordinator runs exactly as in Wave 0 — single-layer, no Master — so the
horizontal ``productivity-core`` path is byte-for-byte unchanged (AC-W1-3.1).
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class StrategicContext(BaseModel):
    """Strategic brief handed from a Master-Agent to its subordinate Coordinator.

    ``parent_task_id`` carries the Master task id so the Coordinator's leaf
    delegations chain under it (AC-W1-3.3). ``vertical_tag`` is the canonical
    underscore slug (e.g. ``agency_marketing_ru``) matching
    ``Cell.vertical_template_slug`` + the seed natural key.
    """

    objective: str = Field(..., min_length=1)
    vertical_tag: str = Field(..., min_length=1)
    domain_constraints: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)
    parent_task_id: UUID | None = None

    def as_coordinator_preamble(self) -> str:
        """Compact domain brief prepended to the Coordinator's prompt.

        Gives the operational Coordinator the Master's strategic framing
        (domain lens + constraints + success criteria) without changing the
        Coordinator's role-prompt or output contract. Returns a markdown block
        the runtime prepends to the objective prompt (AC-W1-3.2).
        """
        lines = [
            "## Стратегический контекст от Master-Agent",
            f"**Вертикаль:** {self.vertical_tag}",
            f"**Стратегическая цель:** {self.objective}",
        ]
        if self.domain_constraints:
            lines.append("**Доменные ограничения:**")
            lines.extend(f"- {c}" for c in self.domain_constraints)
        if self.success_criteria:
            lines.append("**Критерии успеха:**")
            lines.extend(f"- {c}" for c in self.success_criteria)
        return "\n".join(lines)


__all__ = ["StrategicContext"]
