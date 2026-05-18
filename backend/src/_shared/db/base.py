"""DeclarativeBase shared across all bounded-context models.

Phase 00.2 introduces this so iam, multitenancy, audit, etc. can all
inherit the same MetaData (required for cross-context FKs and Alembic
autogenerate in Wave 1+).
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base — every bounded-context model inherits this."""
