"""_shared — cross-cutting utilities consumed by all bounded contexts.

Modules:
    config  — Settings(BaseSettings) loaded from env via pydantic-settings
    logging — configure_structlog() for JSON / console rendering
    db      — async SQLAlchemy session factory + Redis singleton
"""
