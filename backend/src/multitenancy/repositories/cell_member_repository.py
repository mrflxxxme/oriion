"""CellMemberRepository — AsyncSession wrapper for multitenancy.cell_members."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.multitenancy.models import CellMember


class CellMemberRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_cell_user(self, cell_id: UUID, user_id: UUID) -> CellMember | None:
        stmt = select(CellMember).where(
            CellMember.cell_id == cell_id,
            CellMember.user_id == user_id,
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_by_cell(self, cell_id: UUID) -> list[CellMember]:
        stmt = (
            select(CellMember)
            .where(CellMember.cell_id == cell_id)
            .order_by(CellMember.joined_at.asc())
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def add_member(
        self,
        *,
        cell_id: UUID,
        user_id: UUID,
        role_id: UUID,
        invited_by: UUID | None = None,
    ) -> CellMember:
        member = CellMember(
            cell_id=cell_id,
            user_id=user_id,
            role_id=role_id,
            invited_by=invited_by,
        )
        self._session.add(member)
        await self._session.flush()
        return member

    async def update_role(
        self,
        *,
        cell_id: UUID,
        user_id: UUID,
        new_role_id: UUID,
    ) -> None:
        await self._session.execute(
            update(CellMember)
            .where(
                CellMember.cell_id == cell_id,
                CellMember.user_id == user_id,
            )
            .values(role_id=new_role_id)
        )

    async def remove(self, *, cell_id: UUID, user_id: UUID) -> None:
        await self._session.execute(
            delete(CellMember).where(
                CellMember.cell_id == cell_id,
                CellMember.user_id == user_id,
            )
        )
