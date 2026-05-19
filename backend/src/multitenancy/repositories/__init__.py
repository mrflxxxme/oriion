"""multitenancy.repositories — thin AsyncSession wrappers.

Pattern mirrored from src.iam.repositories: no business logic, returns ORM
models or scalars, services do the DTO conversion.
"""
