from typing import Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.classes.models import Class
from src.modules.groups.models import Group
from src.modules.sessions.models import Session
from src.modules.users.models import UserBranch


class ClassRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, class_id: int) -> Optional[Class]:
        result = await self._session.execute(
            select(Class)
            .where(Class.id == class_id)
            .options(
                selectinload(Class.branch),
                selectinload(Class.module),
                selectinload(Class.teacher),
            )
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        search: Optional[str] = None,
        branch_id: Optional[int] = None,
        module_id: Optional[int] = None,
        teacher_id: Optional[int] = None,
        status: str = "active",
        education_stage: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        branch_ids_scope: Optional[list[int]] = None,
    ) -> tuple[list[Class], int]:
        q = (
            select(Class)
            .options(
                selectinload(Class.branch),
                selectinload(Class.module),
                selectinload(Class.teacher),
            )
        )

        if branch_ids_scope is not None:
            q = q.where(Class.branch_id.in_(branch_ids_scope))
        if branch_id:
            q = q.where(Class.branch_id == branch_id)
        if module_id:
            q = q.where(Class.module_id == module_id)
        if teacher_id:
            q = q.where(Class.teacher_id == teacher_id)
        if status and status != "all":
            q = q.where(Class.status == status)
        if education_stage:
            q = q.where(Class.education_stage == education_stage)
        if search:
            q = q.where(Class.name.ilike(f"%{search}%"))

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self._session.execute(count_q)).scalar_one()

        sort_col_map = {
            "name": Class.name,
            "createdAt": Class.created_at,
            "created_at": Class.created_at,
            "periodStart": Class.period_start,
            "levelRank": Class.level_rank,
        }
        col = sort_col_map.get(sort_by, Class.created_at)
        q = q.order_by(col.desc() if sort_order == "desc" else col.asc())
        q = q.offset((page - 1) * page_size).limit(page_size)

        result = await self._session.execute(q)
        return list(result.scalars().all()), total

    async def get_groups_count(self, class_id: int) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(Group).where(Group.class_id == class_id)
        )
        return result.scalar_one()

    async def get_groups_summary(self, class_id: int) -> list[Group]:
        result = await self._session.execute(
            select(Group)
            .where(Group.class_id == class_id, Group.status == "active")
            .order_by(Group.name)
        )
        return list(result.scalars().all())

    async def has_any_sessions(self, class_id: int) -> bool:
        result = await self._session.execute(
            select(func.count(Session.id))
            .join(Group, Group.id == Session.group_id)
            .where(Group.class_id == class_id)
        )
        return result.scalar_one() > 0

    async def teacher_assigned_to_branch(self, teacher_id: int, branch_id: int) -> bool:
        result = await self._session.execute(
            select(func.count()).select_from(UserBranch).where(
                UserBranch.user_id == teacher_id,
                UserBranch.branch_id == branch_id,
            )
        )
        return result.scalar_one() > 0

    async def get_stats(self, branch_ids_scope: Optional[list[int]] = None) -> dict:
        q = select(Class.status, func.count(Class.id)).group_by(Class.status)
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

    async def create(self, cls: Class) -> Class:
        self._session.add(cls)
        await self._session.flush()
        await self._session.refresh(cls)
        return cls

    async def save(self, cls: Class) -> Class:
        merged = await self._session.merge(cls)
        await self._session.flush()
        await self._session.refresh(merged)
        return merged

    async def delete(self, cls: Class) -> None:
        await self._session.delete(cls)
        await self._session.flush()
