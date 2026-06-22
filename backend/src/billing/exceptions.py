"""Billing bounded-context exceptions.

Quota exceptions carry ``code`` / ``status_code`` / ``title`` mirroring the
``tasks.exceptions.TasksError`` shape so the orchestrator's generic failure
handler (``getattr(exc, "code", ...)``) and the API error mapper treat them
uniformly without importing the concrete classes.
"""

from __future__ import annotations


class BillingError(Exception):
    """Base for all billing-domain errors."""

    code: str = "billing.error"
    status_code: int = 500
    title: str = "Billing error"

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail
        super().__init__(detail or self.title)


class PlanNotFound(BillingError):
    """A referenced tariff plan slug is absent from the catalog.

    For a seeded slug (e.g. 'trial') this signals a missing/var-drifted seed —
    an operator-grade 500, not a user error.
    """

    code = "billing.plan_not_found"
    status_code = 500
    title = "Billing plan not found"

    def __init__(self, slug: str) -> None:
        super().__init__(f"billing plan not found: {slug!r}")
        self.slug = slug


class CellQuotaExceeded(BillingError):
    """Per-cell credit cap (period hard-cap) reached — new tasks blocked.

    AC-01.3.5. HTTP 402 if surfaced via the API; in the task path it becomes a
    ``task.failed`` with this code.
    """

    code = "billing.cell_quota_exceeded"
    status_code = 402
    title = "Cell credit quota exceeded"


class DailyQuotaExceeded(BillingError):
    """Per-day credit kill-switch reached (R-04 runaway-cost guard).

    AC-01.3.6. Blocks new task admission for the rest of the UTC day.
    """

    code = "billing.daily_quota_exceeded"
    status_code = 402
    title = "Daily credit quota exceeded"
