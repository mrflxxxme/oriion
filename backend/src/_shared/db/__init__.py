"""_shared.db — async SQLAlchemy + Redis singletons.

Modules:
    base    — DeclarativeBase shared by every bounded context's models
    session — AsyncEngine + AsyncSessionMaker + get_db FastAPI dependency
    redis   — get_redis FastAPI dependency
"""
