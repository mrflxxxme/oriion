"""DeclarativeBase shared across all bounded-context models.

Phase 00.2 introduces this so iam, multitenancy, audit, etc. can all
inherit the same MetaData (required for cross-context FKs and Alembic
autogenerate in Wave 1+).

Phase 00.2.5: added ``type_annotation_map`` so ``Mapped[datetime]`` resolves
to ``TIMESTAMP WITH TIME ZONE`` at the binding layer. The migrations always
create these columns as ``timestamptz`` (see e.g.
``migrations/versions/iam/0005_email_verification_tokens.py:28``), but
without the override SQLAlchemy 2.x picks the default
``TIMESTAMP WITHOUT TIME ZONE`` for ORM inserts — asyncpg then rejects
``datetime.now(UTC) + timedelta(...)`` values with
"can't subtract offset-naive and offset-aware datetimes". The DDL was
already correct; we were just lying about it at the type level.
"""

from __future__ import annotations

from datetime import datetime
from typing import ClassVar

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base — every bounded-context model inherits this."""

    type_annotation_map: ClassVar[dict[type, DateTime]] = {
        datetime: DateTime(timezone=True),
    }
