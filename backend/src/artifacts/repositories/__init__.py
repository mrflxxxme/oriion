"""Artifacts repositories — thin typed wrappers around AsyncSession queries.

RLS scopes every statement to the active tenant cell; explicit ``cell_id``
filters are kept as defense-in-depth (missing GUC ⇒ default-deny already).
"""
