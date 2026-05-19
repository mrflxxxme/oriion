"""audit.repositories — thin SQLAlchemy session wrappers.

No business logic. Each repository:
  - Takes AsyncSession via __init__
  - Returns ORM models or scalars (services do DTO conversion)
  - Uses select()/insert() — UPDATE/DELETE are forbidden by the
    audit.deny_update_delete() trigger anyway, so no such methods exist
"""
