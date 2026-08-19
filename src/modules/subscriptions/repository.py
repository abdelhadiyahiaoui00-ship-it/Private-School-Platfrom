from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.subscriptions.models import Subscription
from src.modules.payments.models import Payment
from src.modules.groups.models import Group
from src.modules.classes.models import Class
from src.modules.users.models import User


class SubscriptionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, sub_id: int) -> Optional[Subscription]:
        result = await self._session.execute(
            select(Subscription)
            .where(Subscription.id == sub_id)
            .options(
                selectinload(Subscription.student),
                selectinload(Subscription.teacher),
                selectinload(Subscription.branch),
                selectinload(Subscription.group).selectinload(Group.class_).selectinload(Class.module),
                selectinload(Subscription.payment)
                    .selectinload(Payment.student),
                selectinload(Subscription.payment)
                    .selectinload(Payment.teacher),
                selectinload(Subscription.payment)
                    .selectinload(Payment.recorder),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_ids(self, sub_ids: list[int]) -> list[Subscription]:
        if not sub_ids:
            return []

        result = await self._session.execute(
            select(Subscription)
            .where(Subscription.id.in_(sub_ids))
            .options(
                selectinload(Subscription.student),
                selectinload(Subscription.teacher),
                selectinload(Subscription.branch),
                selectinload(Subscription.group)
                    .selectinload(Group.class_)
                    .selectinload(Class.module),
                selectinload(Subscription.payment),
            )
        )
        subs_by_id = {sub.id: sub for sub in result.scalars().all()}
        return [subs_by_id[sub_id] for sub_id in sub_ids if sub_id in subs_by_id]

    async def get_latest_for_enrollment(self, enrollment_id: int) -> Optional[Subscription]:
        result = await self._session.execute(
            select(Subscription)
            .where(
                Subscription.enrollment_id == enrollment_id,
                Subscription.status != "cancelled",
            )
            .order_by(Subscription.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        search: Optional[str] = None,
        branch_id: Optional[int] = None,
        branch_ids_scope: Optional[list[int]] = None,
        group_id: Optional[int] = None,
        class_id: Optional[int] = None,
        module_id: Optional[int] = None,
        teacher_id: Optional[int] = None,
        type_: Optional[str] = None,
        status: str = "active",
        expiring_soon_only: bool = False,
        expired_only: bool = False,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        expiry_warning_days: int = 3,
    ) -> tuple[list[Subscription], int]:
        q = (
            select(Subscription)
            .options(
                selectinload(Subscription.student),
                selectinload(Subscription.teacher),
                selectinload(Subscription.branch),
                selectinload(Subscription.group).selectinload(Group.class_).selectinload(Class.module),
                selectinload(Subscription.payment),
            )
        )

        # Branch scoping
        if branch_ids_scope is not None:
            q = q.where(Subscription.branch_id.in_(branch_ids_scope))
        if branch_id:
            q = q.where(Subscription.branch_id == branch_id)

        # Filters
        if group_id:
            q = q.where(Subscription.group_id == group_id)
        if class_id:
            q = (
                q.join(Group, Group.id == Subscription.group_id)
                .where(Group.class_id == class_id)
            )
        if module_id:
            q = q.where(Subscription.module_id == module_id)
        if teacher_id:
            q = q.where(Subscription.teacher_id == teacher_id)
        if type_:
            q = q.where(Subscription.type == type_)
        if status and status != "all":
            q = q.where(Subscription.status == status)

        today = date.today()
        if expiring_soon_only:
            warn_date = today + timedelta(days=expiry_warning_days)
            q = q.where(
                Subscription.status == "active",
                Subscription.end_date.isnot(None),
                Subscription.end_date > today,
                Subscription.end_date <= warn_date,
            )
        if expired_only:
            q = q.where(
                Subscription.status == "active",
                Subscription.end_date.isnot(None),
                Subscription.end_date < today,
            )

        if search:
            term = f"%{search}%"
            q = (
                q.join(User, User.id == Subscription.student_id, isouter=True)
                .where(
                    or_(
                        User.first_name.ilike(term),
                        User.last_name.ilike(term),
                    )
                )
            )

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self._session.execute(count_q)).scalar_one()

        sort_col_map = {
            "created_at": Subscription.created_at,
            "end_date": Subscription.end_date,
            "price": Subscription.price,
        }
        col = sort_col_map.get(sort_by, Subscription.created_at)
        q = q.order_by(col.desc() if sort_order == "desc" else col.asc())
        q = q.offset((page - 1) * page_size).limit(page_size)

        result = await self._session.execute(q)
        return list(result.scalars().all()), total

    async def get_active_for_group(self, group_id: int) -> list[Subscription]:
        """All active subscriptions under a group — used for bulk extend."""
        result = await self._session.execute(
            select(Subscription)
            .where(
                Subscription.group_id == group_id,
                Subscription.status == "active",
            )
            .options(
                selectinload(Subscription.student),
                selectinload(Subscription.teacher),
                selectinload(Subscription.group),
            )
        )
        return list(result.scalars().all())

    async def get_stats(
        self,
        branch_ids_scope: Optional[list[int]] = None,
        expiry_warning_days: int = 3,
    ) -> dict:
        today = date.today()
        warn_date = today + timedelta(days=expiry_warning_days)

        q_base = select(Subscription.status, func.count(Subscription.id)).group_by(
            Subscription.status
        )
        if branch_ids_scope is not None:
            q_base = q_base.where(Subscription.branch_id.in_(branch_ids_scope))

        result = await self._session.execute(q_base)
        rows = result.all()
        stats = {"total": 0, "active": 0, "expiring_soon": 0, "expired": 0, "cancelled": 0}
        for status, cnt in rows:
            stats["total"] += cnt
            if status in stats:
                stats[status] = cnt

        # Compute expiring_soon and expired as sub-counts of active
        base_where = [Subscription.status == "active"]
        if branch_ids_scope is not None:
            base_where.append(Subscription.branch_id.in_(branch_ids_scope))

        soon_q = select(func.count()).select_from(Subscription).where(
            *base_where,
            Subscription.end_date.isnot(None),
            Subscription.end_date > today,
            Subscription.end_date <= warn_date,
        )
        stats["expiring_soon"] = (await self._session.execute(soon_q)).scalar_one()

        exp_q = select(func.count()).select_from(Subscription).where(
            *base_where,
            Subscription.end_date.isnot(None),
            Subscription.end_date < today,
        )
        stats["expired"] = (await self._session.execute(exp_q)).scalar_one()

        return stats

    async def get_latest_subscription_ids(
        self, enrollment_ids: list[int]
    ) -> dict[int, int]:
        """
        Returns {enrollment_id: latest_subscription_id} for a list of enrollment IDs.
        Used for computing isLatestForEnrollment flag efficiently.
        """
        if not enrollment_ids:
            return {}
        subq = (
            select(
                Subscription.enrollment_id,
                func.max(Subscription.id).label("max_id"),
            )
            .where(
                Subscription.enrollment_id.in_(enrollment_ids),
                Subscription.status != "cancelled",
            )
            .group_by(Subscription.enrollment_id)
            .subquery()
        )
        result = await self._session.execute(
            select(subq.c.enrollment_id, subq.c.max_id)
        )
        return {row.enrollment_id: row.max_id for row in result.all()}

    async def create(self, sub: Subscription) -> Subscription:
        self._session.add(sub)
        await self._session.flush()
        await self._session.refresh(sub)
        return sub

    async def save(self, sub: Subscription) -> Subscription:
        merged = await self._session.merge(sub)
        await self._session.flush()
        await self._session.refresh(merged)
        return merged
