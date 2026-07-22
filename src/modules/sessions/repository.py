from datetime import date
from typing import Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.sessions.models import Session


class SessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, session_id: int) -> Optional[Session]:
        from src.modules.groups.models import Group
        from src.modules.classes.models import Class

        result = await self._session.execute(
            select(Session)
            .where(Session.id == session_id)
            .options(
                selectinload(Session.group_).selectinload(Group.class_).selectinload(Class.module),
                selectinload(Session.group_).selectinload(Group.teacher),
                selectinload(Session.group_).selectinload(Group.class_).selectinload(Class.teacher),
            )
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        group_id: Optional[int] = None,
        branch_id: Optional[int] = None,
        teacher_id: Optional[int] = None,
        room: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        branch_ids_scope: Optional[list[int]] = None,
    ) -> tuple[list[Session], int]:
        from src.modules.groups.models import Group
        from src.modules.classes.models import Class

        q = select(Session).join(Session.group_).join(Group.class_).options(
            selectinload(Session.group_).selectinload(Group.class_).selectinload(Class.module),
            selectinload(Session.group_).selectinload(Group.teacher),
            selectinload(Session.group_).selectinload(Group.class_).selectinload(Class.teacher),
        )

        if branch_ids_scope is not None:
            q = q.where(Session.branch_id.in_(branch_ids_scope))
        if branch_id:
            q = q.where(Session.branch_id == branch_id)
        if group_id:
            q = q.where(Session.group_id == group_id)
        if teacher_id:
            q = q.where((Group.teacher_id == teacher_id) | (Class.teacher_id == teacher_id))
        if room:
            q = q.where(Session.room.ilike(f"%{room}%"))
        if from_date:
            q = q.where(Session.session_date >= from_date)
        if to_date:
            q = q.where(Session.session_date <= to_date)
        if status:
            q = q.where(Session.status == status)

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self._session.execute(count_q)).scalar_one()

        q = q.order_by(Session.session_date.desc(), Session.start_time.desc())
        q = q.offset((page - 1) * page_size).limit(page_size)

        result = await self._session.execute(q)
        return list(result.scalars().all()), total

    async def save(self, sess: Session) -> Session:
        merged = await self._session.merge(sess)
        await self._session.flush()
        await self._session.refresh(merged)
        return merged

    async def delete(self, sess: Session) -> None:
        await self._session.delete(sess)
        await self._session.flush()
