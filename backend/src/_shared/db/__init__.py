"""_shared.db — async SQLAlchemy + Redis singletons + RLS context-setter.

Modules:
    base    — DeclarativeBase shared by every bounded context's models
    session — AsyncEngine + AsyncSessionMaker + get_db FastAPI dependency
    redis   — get_redis FastAPI dependency
    rls     — set_tenant_context (3-GUC layered model per ADR-009 amendment 2026-05-19)
"""

from src._shared.db.rls import clear_tenant_context, set_tenant_context

__all__ = ["clear_tenant_context", "set_tenant_context"]
