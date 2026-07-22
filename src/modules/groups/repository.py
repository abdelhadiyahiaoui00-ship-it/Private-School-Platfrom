from typing import Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.groups.models import Group
from src.modules.sessions.models import Session
from src.modules.enrollments.models import Enrollment


class GroupRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, group_id: int) -> Optional[Group]:
        result = await self._session.execute(
            select(Group)
            .where(Group.id == group_id)
            .options(
                selectinload(Group.class_).selectinload("module"),
                selectinload(Group.teacher),
            )
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        class_id: Optional[int] = None,
        branch_id: Optional[int] = None,
        teacher_id: Optional[int] = None,
        status: str = "active",
        page: int = 1,
        page_size: int = 20,
        branch_ids_scope: Optional[list[int]] = None,
    ) -> tuple[list[Group], int]:
        from src.modules.classes.models import Class
        
        q = select(Group).join(Group.class_).options(
            selectinload(Group.class_).selectinload("module"),
            selectinload(Group.teacher)
        )

        if branch_ids_scope is not None:
            q = q.where(Class.branch_id.in_(branch_ids_scope))
        if branch_id:
            q = q.where(Class.branch_id == branch_id)
        if class_id:
            q = q.where(Group.class_id == class_id)
        if teacher_id:
            q = q.where(Group.teacher_id == teacher_id)
        if status and status != "all":
            q = q.where(Group.status == status)

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self._session.execute(count_q)).scalar_one()

        q = q.order_by(Group.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self._session.execute(q)
        return list(result.scalars().all()), total

    async def has_active_enrollments(self, group_id: int) -> bool:
        result = await self._session.execute(
            select(func.count(Enrollment.id)).where(
                Enrollment.group_id == group_id,
                Enrollment.status == "active"
            )
        )
        return result.scalar_one() > 0

    async def has_any_dependencies(self, group_id: int) -> bool:
        c1 = await self._session.execute(select(func.count(Enrollment.id)).where(Enrollment.group_id == group_id))
        if c1.scalar_one() > 0:
            return True
        c2 = await self._session.execute(select(func.count(Session.id)).where(Session.group_id == group_id))
        return c2.scalar_one() > 0

    async def get_stats(self, branch_ids_scope: Optional[list[int]] = None) -> dict:
        from src.modules.classes.models import Class
        q = select(Group.status, func.count(Group.id)).join(Group.class_).group_by(Group.status)
        if branch_ids_scope is not None:
            q = q.where(Class.branch_id.in_(branch_ids_scope))
        result = await self._session.execute(q)
        rows = result.all()
        stats: dict = {"total": 0, "active": 0, "archived": 0}
        for status, cnt in rows:
            stats["total"] += cnt
            if status == "active":
                stats["active"] = cnt
            elif status == "archived":
                stats["archived"] = cnt
        return stats

    async def create(self, group: Group) -> Group:
        self._session.add(group)
        await self._session.flush()
        await self._session.refresh(group)
        return group

    async def save(self, group: Group) -> Group:
        merged = await self._session.merge(group)
        await self._session.flush()
        await self._session.refresh(merged)
        return merged

    async def delete(self, group: Group) -> None:
        await self._session.delete(group)
        await self._session.flush()
