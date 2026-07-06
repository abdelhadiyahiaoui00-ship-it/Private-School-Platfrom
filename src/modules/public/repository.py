import logging
from datetime import date
from typing import Optional

from sqlalchemy import and_, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.config import settings
from src.modules.branches.models import Branch
from src.modules.classes.models import Class
from src.modules.enrollments.models import Enrollment
from src.modules.groups.models import Group
from src.modules.sessions.models import Session

logger = logging.getLogger(settings.APP_NAME)


class PublicRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_active_groups(
        self,
        search: Optional[str] = None,
        branch_id: Optional[int] = None,
        module_id: Optional[int] = None,
        day_of_week: Optional[int] = None,
        subscription_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 12,
    ) -> tuple[list[Group], int]:
        """Returns active groups from active classes in active branches."""
        from src.modules.modules.models import Module

        q = (
            select(Group)
            .join(Class, Class.id == Group.class_id)
            .join(Branch, Branch.id == Class.branch_id)
            .where(
                Group.status == "active",
                Class.status == "active",
                Branch.is_active == True,  # noqa: E712
            )
            .options(selectinload(Group.class_), selectinload(Group.teacher))
        )

        if branch_id:
            q = q.where(Class.branch_id == branch_id)

        if module_id:
            q = q.where(Class.module_id == module_id)

        if subscription_type:
            q = q.where(Group.subscription_type == subscription_type)

        if search:
            q = q.join(Module, Module.id == Class.module_id, isouter=True)
            term = f"%{search}%"
            q = q.where(Module.name.ilike(term))

        if day_of_week is not None:
            # PostgreSQL JSONB contains filter
            q = q.where(
                text(f"schedule::jsonb @> '[{{\"dayOfWeek\": {int(day_of_week)}}}]'")
            )

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self._session.execute(count_q)).scalar_one()

        q = q.offset((page - 1) * page_size).limit(page_size)
        result = await self._session.execute(q)
        return list(result.scalars().all()), total

    async def get_featured_groups(self, limit: int = 6) -> list[Group]:
        """Top groups by active enrollment count."""
        enrollment_count = (
            select(Enrollment.group_id, func.count(Enrollment.id).label("cnt"))
            .where(Enrollment.status == "active")
            .group_by(Enrollment.group_id)
            .subquery()
        )

        q = (
            select(Group)
            .join(Class, Class.id == Group.class_id)
            .join(Branch, Branch.id == Class.branch_id)
            .outerjoin(enrollment_count, enrollment_count.c.group_id == Group.id)
            .where(
                Group.status == "active",
                Class.status == "active",
                Branch.is_active == True,  # noqa: E712
            )
            .options(selectinload(Group.class_), selectinload(Group.teacher))
            .order_by(func.coalesce(enrollment_count.c.cnt, 0).desc())
            .limit(limit)
        )

        result = await self._session.execute(q)
        return list(result.scalars().all())

    async def get_group_by_id(self, group_id: int) -> Optional[Group]:
        """Get single active group by ID."""
        q = (
            select(Group)
            .join(Class, Class.id == Group.class_id)
            .join(Branch, Branch.id == Class.branch_id)
            .where(
                Group.id == group_id,
                Group.status == "active",
                Class.status == "active",
                Branch.is_active == True,  # noqa: E712
            )
            .options(selectinload(Group.class_), selectinload(Group.teacher))
        )
        result = await self._session.execute(q)
        return result.scalar_one_or_none()

    async def get_active_enrollment_count(self, group_id: int) -> int:
        """Count active enrollments for a group."""
        result = await self._session.execute(
            select(func.count(Enrollment.id))
            .where(
                Enrollment.group_id == group_id,
                Enrollment.status == "active",
            )
        )
        return result.scalar_one()

    async def get_enrollment_counts_bulk(self, group_ids: list[int]) -> dict[int, int]:
        """Get active enrollment counts for multiple groups at once — avoids N+1."""
        if not group_ids:
            return {}
        result = await self._session.execute(
            select(Enrollment.group_id, func.count(Enrollment.id).label("cnt"))
            .where(
                Enrollment.group_id.in_(group_ids),
                Enrollment.status == "active",
            )
            .group_by(Enrollment.group_id)
        )
        return {row.group_id: row.cnt for row in result.all()}

    async def get_upcoming_sessions(
        self, group_id: int, limit: int = 3
    ) -> list[Session]:
        """Get next N upcoming sessions for a group."""
        today = date.today()
        result = await self._session.execute(
            select(Session)
            .where(
                Session.group_id == group_id,
                Session.session_date >= today,
                Session.status == "scheduled",
            )
            .order_by(Session.session_date.asc(), Session.start_time.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_filter_options(self) -> dict:
        """Get available branches and modules for catalog filters."""
        from src.modules.modules.models import Module

        branches_q = (
            select(Branch.id, Branch.name)
            .join(Class, Class.branch_id == Branch.id)
            .join(Group, Group.class_id == Class.id)
            .where(
                Branch.is_active == True,  # noqa: E712
                Class.status == "active",
                Group.status == "active",
            )
            .distinct()
            .order_by(Branch.name)
        )
        branches_result = await self._session.execute(branches_q)
        branches = [{"id": r.id, "name": r.name} for r in branches_result.all()]

        modules_q = (
            select(Module.id, Module.name)
            .join(Class, Class.module_id == Module.id)
            .join(Group, Group.class_id == Class.id)
            .where(
                Class.status == "active",
                Group.status == "active",
                Module.is_active == True,  # noqa: E712
            )
            .distinct()
            .order_by(Module.name)
        )
        modules_result = await self._session.execute(modules_q)
        modules = [{"id": r.id, "name": r.name} for r in modules_result.all()]

        return {"branches": branches, "modules": modules}

    async def get_active_classes_count(self, branch_id: int) -> int:
        """Count active classes for a branch."""
        result = await self._session.execute(
            select(func.count(Class.id))
            .where(
                Class.branch_id == branch_id,
                Class.status == "active",
            )
        )
        return result.scalar_one()

    async def get_active_branches(self) -> list[Branch]:
        """Get all active branches ordered by created_at ASC."""
        result = await self._session.execute(
            select(Branch)
            .where(Branch.is_active == True)  # noqa: E712
            .order_by(Branch.created_at.asc())
        )
        return list(result.scalars().all())
