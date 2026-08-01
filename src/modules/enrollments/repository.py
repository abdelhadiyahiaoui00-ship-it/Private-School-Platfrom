from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.enrollments.models import Enrollment
from src.modules.enrollments.visitor_models import VisitorEnrollmentRequest
from src.modules.groups.models import Group
from src.modules.classes.models import Class
from src.modules.users.models import ParentStudentLink, User


class EnrollmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, enrollment_id: int) -> Optional[Enrollment]:
        result = await self._session.execute(
            select(Enrollment)
            .where(Enrollment.id == enrollment_id)
            .options(
                selectinload(Enrollment.student),
                selectinload(Enrollment.group),
                selectinload(Enrollment.visitor_request),
            )
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        search: Optional[str] = None,
        branch_id: Optional[int] = None,
        branch_ids_scope: Optional[list[int]] = None,
        group_id: Optional[int] = None,
        class_id: Optional[int] = None,
        status: Optional[str] = None,
        source: Optional[str] = None,
        overdue_only: bool = False,
        hold_hours: int = 72,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[Enrollment], int]:
        q = (
            select(Enrollment)
            .options(
                selectinload(Enrollment.student),
                selectinload(Enrollment.group),
                selectinload(Enrollment.visitor_request),
            )
        )

        if branch_ids_scope is not None:
            q = q.where(Enrollment.branch_id.in_(branch_ids_scope))
        if branch_id:
            q = q.where(Enrollment.branch_id == branch_id)
        if group_id:
            q = q.where(Enrollment.group_id == group_id)
        if class_id:
            q = q.join(Group, Group.id == Enrollment.group_id).where(Group.class_id == class_id)
        if status and status != "all":
            statuses = [s.strip() for s in status.split(",")]
            q = q.where(Enrollment.status.in_(statuses))
        else:
            # Default: pending + waitlisted
            if not status:
                q = q.where(Enrollment.status.in_(["pending", "waitlisted"]))
        if source:
            q = q.where(Enrollment.source == source)
        if overdue_only:
            # isOverdue: pending + visitor_form + past hold window
            from datetime import timedelta
            cutoff = datetime.now(timezone.utc) - timedelta(hours=hold_hours)
            q = q.where(
                Enrollment.status == "pending",
                Enrollment.source == "visitor_form",
                Enrollment.created_at < cutoff,
            )
        if search:
            term = f"%{search}%"
            q = q.join(User, User.id == Enrollment.student_id, isouter=True).where(
                or_(
                    User.first_name.ilike(term),
                    User.last_name.ilike(term),
                    User.phone.ilike(term),
                )
            )

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self._session.execute(count_q)).scalar_one()

        sort_col = Enrollment.created_at if sort_by == "created_at" else Enrollment.waitlist_position
        q = q.order_by(sort_col.desc() if sort_order == "desc" else sort_col.asc())
        q = q.offset((page - 1) * page_size).limit(page_size)

        result = await self._session.execute(q)
        return list(result.scalars().all()), total

    async def get_my_enrollments(
        self,
        student_id: Optional[int] = None,
        student_ids: Optional[list[int]] = None,
        status: Optional[str] = None,
    ) -> list[Enrollment]:
        """For student (single studentId) or parent (list of child studentIds)."""
        q = select(Enrollment).options(
            selectinload(Enrollment.student),
            selectinload(Enrollment.group),
        )
        if student_id:
            q = q.where(Enrollment.student_id == student_id)
        elif student_ids:
            q = q.where(Enrollment.student_id.in_(student_ids))

        if status:
            statuses = [s.strip() for s in status.split(",")]
            q = q.where(Enrollment.status.in_(statuses))

        q = q.order_by(Enrollment.created_at.desc())
        result = await self._session.execute(q)
        return list(result.scalars().all())

    async def count_active_enrollments(self, group_id: int) -> int:
        """Count pending + active enrollments for capacity check."""
        result = await self._session.execute(
            select(func.count()).select_from(Enrollment).where(
                Enrollment.group_id == group_id,
                Enrollment.status.in_(["pending", "active"]),
            )
        )
        return result.scalar_one()

    async def get_max_waitlist_position(self, group_id: int) -> int:
        """Get current highest waitlist position for a group (0 if none)."""
        result = await self._session.execute(
            select(func.max(Enrollment.waitlist_position)).where(
                Enrollment.group_id == group_id,
                Enrollment.status == "waitlisted",
            )
        )
        return result.scalar_one() or 0

    async def get_next_in_waitlist(self, group_id: int) -> Optional[Enrollment]:
        """Get the first (lowest position) waitlisted enrollment for a group."""
        result = await self._session.execute(
            select(Enrollment)
            .where(
                Enrollment.group_id == group_id,
                Enrollment.status == "waitlisted",
            )
            .order_by(Enrollment.waitlist_position.asc())
            .limit(1)
            .options(selectinload(Enrollment.student))
        )
        return result.scalar_one_or_none()

    async def resequence_waitlist(self, group_id: int) -> None:
        """Re-sequence waitlist positions to be contiguous starting at 1."""
        rows = await self._session.execute(
            select(Enrollment)
            .where(
                Enrollment.group_id == group_id,
                Enrollment.status == "waitlisted",
            )
            .order_by(Enrollment.waitlist_position.asc())
        )
        enrollments = list(rows.scalars().all())
        for i, e in enumerate(enrollments, start=1):
            e.waitlist_position = i
        await self._session.flush()

    async def has_active_enrollment(self, group_id: int, student_id: int) -> bool:
        """Check for duplicate non-terminal enrollment."""
        result = await self._session.execute(
            select(func.count()).select_from(Enrollment).where(
                Enrollment.group_id == group_id,
                Enrollment.student_id == student_id,
                Enrollment.status.in_(["pending", "waitlisted", "active"]),
            )
        )
        return result.scalar_one() > 0

    async def get_stats(
        self,
        branch_ids_scope: Optional[list[int]] = None,
        hold_hours: int = 72,
    ) -> dict:
        from datetime import timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hold_hours)

        q_base = select(Enrollment.status, func.count(Enrollment.id)).group_by(Enrollment.status)
        if branch_ids_scope is not None:
            q_base = q_base.where(Enrollment.branch_id.in_(branch_ids_scope))
        result = await self._session.execute(q_base)
        rows = result.all()
        pending_count = waitlisted_count = 0
        for status, cnt in rows:
            if status == "pending":
                pending_count = cnt
            elif status == "waitlisted":
                waitlisted_count = cnt

        overdue_q = select(func.count()).select_from(Enrollment).where(
            Enrollment.status == "pending",
            Enrollment.source == "visitor_form",
            Enrollment.created_at < cutoff,
        )
        if branch_ids_scope is not None:
            overdue_q = overdue_q.where(Enrollment.branch_id.in_(branch_ids_scope))
        overdue_count = (await self._session.execute(overdue_q)).scalar_one()

        return {
            "pending_count": pending_count,
            "waitlisted_count": waitlisted_count,
            "overdue_count": overdue_count,
        }

    async def create(self, enrollment: Enrollment) -> Enrollment:
        self._session.add(enrollment)
        await self._session.flush()
        await self._session.refresh(enrollment)
        return enrollment

    async def save(self, enrollment: Enrollment) -> Enrollment:
        merged = await self._session.merge(enrollment)
        await self._session.flush()
        await self._session.refresh(merged)
        return merged

    async def get_parent_child_ids(self, parent_user_id: int) -> list[int]:
        """Get all student IDs linked to a parent."""
        result = await self._session.execute(
            select(ParentStudentLink.student_id)
            .where(ParentStudentLink.parent_id == parent_user_id)
        )
        return [row[0] for row in result.all()]

    async def is_linked_child(self, parent_user_id: int, student_id: int) -> bool:
        result = await self._session.execute(
            select(func.count()).select_from(ParentStudentLink).where(
                ParentStudentLink.parent_id == parent_user_id,
                ParentStudentLink.student_id == student_id,
            )
        )
        return result.scalar_one() > 0


class VisitorRequestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, request_id: int) -> Optional[VisitorEnrollmentRequest]:
        result = await self._session.execute(
            select(VisitorEnrollmentRequest)
            .where(VisitorEnrollmentRequest.id == request_id)
            .options(selectinload(VisitorEnrollmentRequest.enrollment))
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        status: Optional[str] = "pending",
        branch_id: Optional[int] = None,
        branch_ids_scope: Optional[list[int]] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[VisitorEnrollmentRequest], int]:
        q = (
            select(VisitorEnrollmentRequest)
            .options(
                selectinload(VisitorEnrollmentRequest.enrollment)
                .selectinload(Enrollment.student)
            )
        )

        if status and status != "all":
            q = q.where(VisitorEnrollmentRequest.status == status)
        if branch_ids_scope is not None or branch_id:
            q = q.join(Enrollment, Enrollment.id == VisitorEnrollmentRequest.enrollment_id)
            if branch_ids_scope is not None:
                q = q.where(Enrollment.branch_id.in_(branch_ids_scope))
            if branch_id:
                q = q.where(Enrollment.branch_id == branch_id)
        if search:
            term = f"%{search}%"
            q = q.where(
                or_(
                    VisitorEnrollmentRequest.first_name.ilike(term),
                    VisitorEnrollmentRequest.last_name.ilike(term),
                    VisitorEnrollmentRequest.contact_phone.ilike(term),
                )
            )

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self._session.execute(count_q)).scalar_one()

        q = q.order_by(VisitorEnrollmentRequest.created_at.desc())
        q = q.offset((page - 1) * page_size).limit(page_size)

        result = await self._session.execute(q)
        return list(result.scalars().all()), total

    async def get_stats(self, branch_ids_scope: Optional[list[int]] = None) -> dict:
        q = (
            select(VisitorEnrollmentRequest.status, func.count(VisitorEnrollmentRequest.id))
            .group_by(VisitorEnrollmentRequest.status)
        )
        if branch_ids_scope is not None:
            q = (
                q.join(Enrollment, Enrollment.id == VisitorEnrollmentRequest.enrollment_id)
                .where(Enrollment.branch_id.in_(branch_ids_scope))
            )
        result = await self._session.execute(q)
        rows = result.all()
        stats = {"pending": 0, "converted": 0, "rejected": 0}
        for status, cnt in rows:
            if status in stats:
                stats[status] = cnt
        return stats

    async def create(self, req: VisitorEnrollmentRequest) -> VisitorEnrollmentRequest:
        self._session.add(req)
        await self._session.flush()
        await self._session.refresh(req)
        return req

    async def save(self, req: VisitorEnrollmentRequest) -> VisitorEnrollmentRequest:
        merged = await self._session.merge(req)
        await self._session.flush()
        await self._session.refresh(merged)
        return merged
