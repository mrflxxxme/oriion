"""Billing bounded-context exceptions."""

from __future__ import annotations


class BillingError(Exception):
    """Base for all billing-domain errors."""


class PlanNotFound(BillingError):
    """A referenced tariff plan slug is absent from the catalog.

    For a seeded slug (e.g. 'trial') this signals a missing/var-drifted seed —
    an operator-grade 500, not a user error.
    """

    def __init__(self, slug: str) -> None:
        super().__init__(f"billing plan not found: {slug!r}")
        self.slug = slug
