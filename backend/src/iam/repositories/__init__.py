"""iam.repositories — thin SQLAlchemy session wrappers.

No business logic. Each repository:
  - Owns one aggregate root (or a single auxiliary table)
  - Takes AsyncSession via __init__
  - Returns ORM models or scalars; no DTO conversion (that's services' job)
  - Uses select()/insert()/update() — never raw SQL except for COMMENT/etc.
"""
