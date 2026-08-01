from datetime import date
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
        from src.modules.classes.models import Class
        result = await self._session.execute(
            select(Group)
            .where(Group.id == group_id)
            .options(
                selectinload(Group.class_).selectinload(Class.module),
                selectinload(Group.class_).selectinload(Class.branch),
                selectinload(Group.teacher),
            )
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        class_id: Optional[int] = None,
        branch_id: Optional[int] = None,
        branch_ids: Optional[list[int]] = None,
        teacher_id: Optional[int] = None,
        status: str = "active",
        has_availability: Optional[bool] = None,
        exclude_group_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 20,
        branch_ids_scope: Optional[list[int]] = None,
    ) -> tuple[list[Group], int]:
        from src.modules.classes.models import Class
        
        q = select(Group).join(Group.class_).options(
            selectinload(Group.class_).selectinload(Class.module),
            selectinload(Group.class_).selectinload(Class.branch),
            selectinload(Group.teacher)
        )

        # Effective branch filter — branchId wins; then branchIds; then scope default
        effective_ids: Optional[list[int]] = None
        if branch_id:
            effective_ids = [branch_id] if (branch_ids_scope is None or branch_id in branch_ids_scope) else [-1]
        elif branch_ids:
            effective_ids = branch_ids if branch_ids_scope is None else [b for b in branch_ids if b in branch_ids_scope] or [-1]
        elif branch_ids_scope is not None:
            effective_ids = branch_ids_scope

        if effective_ids is not None:
            q = q.where(Class.branch_id.in_(effective_ids))
        if class_id:
            q = q.where(Group.class_id == class_id)
        if teacher_id:
            q = q.where(Group.teacher_id == teacher_id)
        if status and status != "all":
            q = q.where(Group.status == status)
        if exclude_group_id:
            q = q.where(Group.id != exclude_group_id)
            
        if has_availability is not None:
            # Subquery to count active+pending enrollments
            active_counts = (
                select(Enrollment.group_id, func.count(Enrollment.id).label("active_count"))
                .where(Enrollment.status.in_(["pending", "active"]))
                .group_by(Enrollment.group_id)
                .subquery()
            )
            q = q.outerjoin(active_counts, active_counts.c.group_id == Group.id)
            if has_availability:
                # Group max_students > active_count
                q = q.where(Group.max_students > func.coalesce(active_counts.c.active_count, 0))
            else:
                q = q.where(Group.max_students <= func.coalesce(active_counts.c.active_count, 0))

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

    async def count_active_enrollments(self, group_id: int) -> int:
        result = await self._session.execute(
            select(func.count(Enrollment.id)).where(
                Enrollment.group_id == group_id,
                Enrollment.status.in_(["pending", "active"])
            )
        )
        return result.scalar_one()

    async def get_sessions_count(self, group_id: int) -> int:
        result = await self._session.execute(
            select(func.count(Session.id)).where(Session.group_id == group_id)
        )
        return result.scalar_one()

    async def get_next_session_date(self, group_id: int) -> Optional[date]:
        from datetime import date
        result = await self._session.execute(
            select(Session.session_date)
            .where(Session.group_id == group_id, Session.session_date >= date.today())
            .order_by(Session.session_date.asc())
            .limit(1)
        )
        return result.scalar_one_or_none()

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
