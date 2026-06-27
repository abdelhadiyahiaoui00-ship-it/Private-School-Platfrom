from typing import Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.branches.models import Branch
from src.modules.users.models import UserBranch


class BranchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, branch_id: int) -> Optional[Branch]:
        result = await self._session.execute(
            select(Branch).where(Branch.id == branch_id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Branch], int]:
        q = select(Branch)
        if search:
            q = q.where(Branch.name.ilike(f"%{search}%"))
        if is_active is not None:
            q = q.where(Branch.is_active == is_active)

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self._session.execute(count_q)).scalar_one()

        q = q.order_by(Branch.name.asc()).offset((page - 1) * page_size).limit(page_size)
        result = await self._session.execute(q)
        return list(result.scalars().all()), total

    async def get_all_for_owner(self) -> list[Branch]:
        """All branches (including inactive) for owner/superAdmin."""
        result = await self._session.execute(
            select(Branch).order_by(Branch.name.asc())
        )
        return list(result.scalars().all())

    async def get_assigned_for_admin(self, user_id: int) -> list[Branch]:
        """Active branches assigned to a specific admin/teacher."""
        result = await self._session.execute(
            select(Branch)
            .join(UserBranch, UserBranch.branch_id == Branch.id)
            .where(UserBranch.user_id == user_id, Branch.is_active == True)  # noqa: E712
            .order_by(Branch.name.asc())
        )
        return list(result.scalars().all())

    async def name_exists(self, name: str, exclude_id: Optional[int] = None) -> bool:
        q = select(func.count()).select_from(Branch).where(Branch.name == name)
        if exclude_id:
            q = q.where(Branch.id != exclude_id)
        result = await self._session.execute(q)
        return result.scalar_one() > 0

    async def get_stats(self) -> dict:
        result = await self._session.execute(
            select(Branch.is_active, func.count(Branch.id)).group_by(Branch.is_active)
        )
        rows = result.all()
        total = active = inactive = 0
        for is_active_val, cnt in rows:
            total += cnt
            if is_active_val:
                active += cnt
            else:
                inactive += cnt
        return {"total": total, "active": active, "inactive": inactive}

    async def get_total_users_count(self, branch_id: int) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(UserBranch).where(
                UserBranch.branch_id == branch_id
            )
        )
        return result.scalar_one()

    async def create(self, branch: Branch) -> Branch:
        self._session.add(branch)
        await self._session.flush()
        await self._session.refresh(branch)
        return branch

    async def save(self, branch: Branch) -> Branch:
        merged = await self._session.merge(branch)
        await self._session.flush()
        await self._session.refresh(merged)
        return merged

    async def delete(self, branch: Branch) -> None:
        await self._session.delete(branch)
        await self._session.flush()
