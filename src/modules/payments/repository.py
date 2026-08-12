from datetime import datetime
from typing import Optional
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.payments.models import Payment
from src.modules.users.models import User


class PaymentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, payment_id: int) -> Optional[Payment]:
        result = await self._session.execute(
            select(Payment)
            .where(Payment.id == payment_id)
            .options(
                selectinload(Payment.student),
                selectinload(Payment.teacher),
                selectinload(Payment.recorder),
            )
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        search: Optional[str] = None,
        branch_id: Optional[int] = None,
        branch_ids_scope: Optional[list[int]] = None,
        teacher_id: Optional[int] = None,
        module_id: Optional[int] = None,
        method: Optional[str] = None,
        payment_type: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "recorded_at",
        sort_order: str = "desc",
    ) -> tuple[list[Payment], int]:
        q = select(Payment)

        if branch_ids_scope is not None:
            q = q.where(Payment.branch_id.in_(branch_ids_scope))
        if branch_id:
            q = q.where(Payment.branch_id == branch_id)
        if teacher_id:
            q = q.where(Payment.teacher_id == teacher_id)
        if module_id:
            q = q.where(Payment.module_id == module_id)
        if method:
            q = q.where(Payment.method == method)
        if payment_type:
            q = q.where(Payment.payment_type == payment_type)
        if date_from:
            q = q.where(Payment.recorded_at >= date_from)
        if date_to:
            q = q.where(Payment.recorded_at <= date_to)
        if search:
            term = f"%{search}%"
            q = q.join(User, User.id == Payment.student_id, isouter=True).where(
                or_(User.first_name.ilike(term), User.last_name.ilike(term))
            )

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self._session.execute(count_q)).scalar_one()

        # Apply eager loading after count
        q = q.options(
            selectinload(Payment.student),
            selectinload(Payment.teacher),
            selectinload(Payment.recorder),
            selectinload(Payment.subscription),
            selectinload(Payment.branch),
            selectinload(Payment.class_),
            selectinload(Payment.module),
        )

        sort_col = Payment.recorded_at if sort_by in ["recorded_at", "recordedAt"] else Payment.amount
        q = q.order_by(sort_col.desc() if sort_order == "desc" else sort_col.asc())
        q = q.offset((page - 1) * page_size).limit(page_size)

        result = await self._session.execute(q)
        return list(result.scalars().all()), total

    async def get_summary(
        self,
        branch_ids_scope: Optional[list[int]] = None,
        branch_id: Optional[int] = None,
        teacher_id: Optional[int] = None,
        module_id: Optional[int] = None,
        method: Optional[str] = None,
        payment_type: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> dict:
        """Compute aggregate totals for the current filter — same WHERE conditions as get_all."""
        q = select(
            func.coalesce(func.sum(Payment.amount), 0).label("total_amount"),
            func.coalesce(func.sum(Payment.commission_amount), 0).label("total_commission"),
            func.coalesce(func.sum(Payment.net_amount), 0).label("total_net"),
            func.count(Payment.id).label("count"),
        )
        if branch_ids_scope is not None:
            q = q.where(Payment.branch_id.in_(branch_ids_scope))
        if branch_id:
            q = q.where(Payment.branch_id == branch_id)
        if teacher_id:
            q = q.where(Payment.teacher_id == teacher_id)
        if module_id:
            q = q.where(Payment.module_id == module_id)
        if method:
            q = q.where(Payment.method == method)
        if payment_type:
            q = q.where(Payment.payment_type == payment_type)
        if date_from:
            q = q.where(Payment.recorded_at >= date_from)
        if date_to:
            q = q.where(Payment.recorded_at <= date_to)

        result = await self._session.execute(q)
        row = result.one()
        return {
            "total_amount": float(row.total_amount),
            "total_commission": float(row.total_commission),
            "total_net": float(row.total_net),
            "count": row.count,
        }

    async def create(self, payment: Payment) -> Payment:
        self._session.add(payment)
        await self._session.flush()
        await self._session.refresh(payment)
        return payment
