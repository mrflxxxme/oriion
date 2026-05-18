"""User repository — thin AsyncSession wrapper for iam.users."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.iam.models import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_email(self, email: str) -> User | None:
        """Case-insensitive lookup (CITEXT handles it). Excludes soft-deleted."""
        stmt = select(User).where(
            User.email == email,
            User.deleted_at.is_(None),
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def find_by_id(self, user_id: UUID) -> User | None:
        return await self._session.get(User, user_id)

    async def create(
        self,
        *,
        email: str,
        password_hash: str,
        display_name: str | None = None,
        locale: str = "ru-RU",
    ) -> User:
        user = User(
            email=email,
            password_hash=password_hash,
            display_name=display_name,
            locale=locale,
        )
        self._session.add(user)
        await self._session.flush()
        return user

    async def mark_email_verified(self, user_id: UUID) -> None:
        await self._session.execute(
            update(User).where(User.id == user_id).values(email_verified_at=datetime.now(UTC))
        )

    async def update_password_hash(self, user_id: UUID, new_hash: str) -> None:
        await self._session.execute(
            update(User).where(User.id == user_id).values(password_hash=new_hash)
        )

    async def update_profile(
        self,
        user_id: UUID,
        *,
        display_name: str | None = None,
        locale: str | None = None,
        timezone: str | None = None,
    ) -> None:
        values: dict[str, str | None] = {}
        if display_name is not None:
            values["display_name"] = display_name
        if locale is not None:
            values["locale"] = locale
        if timezone is not None:
            values["timezone"] = timezone
        if not values:
            return
        await self._session.execute(update(User).where(User.id == user_id).values(**values))

    async def soft_delete(self, user_id: UUID) -> None:
        await self._session.execute(
            update(User).where(User.id == user_id).values(deleted_at=datetime.now(UTC))
        )
