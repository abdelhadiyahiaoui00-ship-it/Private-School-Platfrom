from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.pagination import build_pagination
from src.modules.payments.models import Payment
from src.modules.payments.repository import PaymentRepository
from src.modules.payments.schemas import PaymentResponse, PaymentSummary
from src.modules.enrollments.schemas import StudentBasic
from src.modules.classes.schemas import TeacherBasic
from src.modules.users.models import User


def _student_basic(user) -> StudentBasic:
    if not user:
        return StudentBasic(id=0, first_name="", last_name="", avatar_url=None, date_of_birth=None)
    return StudentBasic(
        id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        avatar_url=user.avatar_url,
        date_of_birth=user.date_of_birth,
    )


def _teacher_basic(user) -> TeacherBasic:
    if not user:
        return TeacherBasic(id=0, first_name="", last_name="", avatar_url=None)
    return TeacherBasic(
        id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        avatar_url=user.avatar_url,
        default_commission_percent=float(user.default_commission_percent)
        if user.default_commission_percent is not None else None,
    )


async def _build_payment_response(payment: Payment, db: AsyncSession) -> PaymentResponse:
    from src.modules.branches.models import Branch
    from src.modules.modules.models import Module

    branch_result = await db.execute(
        select(Branch).where(Branch.id == payment.branch_id)
    )
    branch = branch_result.scalar_one_or_none()

    module = None
    if payment.module_id:
        m_result = await db.execute(
            select(Module).where(Module.id == payment.module_id)
        )
        module = m_result.scalar_one_or_none()

    recorder_name = ""
    if payment.recorder:
        recorder_name = f"{payment.recorder.first_name} {payment.recorder.last_name}"

    return PaymentResponse(
        id=payment.id,
        subscription_id=payment.subscription_id,
        enrollment_id=payment.enrollment_id,
        student_id=payment.student_id,
        student=_student_basic(payment.student),
        branch_id=payment.branch_id,
        branch_name=branch.name if branch else "",
        class_id=payment.class_id,
        module_id=payment.module_id,
        module_name=module.name if module else "",
        teacher_id=payment.teacher_id,
        teacher=_teacher_basic(payment.teacher),
        amount=float(payment.amount),
        currency=payment.currency,
        method=payment.method,
        commission_percent=float(payment.commission_percent),
        commission_amount=float(payment.commission_amount),
        net_amount=float(payment.net_amount),
        payment_type=payment.payment_type,
        recorded_by=payment.recorded_by,
        recorded_by_name=recorder_name,
        recorded_at=payment.recorded_at,
        notes=payment.notes,
    )


class PaymentService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = PaymentRepository(session)

    def _get_branch_scope(self, actor: User) -> Optional[list[int]]:
        if actor.role in ("owner", "superAdmin"):
            return None
        return [ub.branch_id for ub in (actor.branch_links or [])]

    def _parse_date(self, value) -> Optional[datetime]:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        return value

    async def list_payments(self, filters: dict, actor: User) -> dict:
        branch_ids_scope = self._get_branch_scope(actor)

        payments, total = await self._repo.get_all(
            search=filters.get("search"),
            branch_id=filters.get("branch_id"),
            branch_ids_scope=branch_ids_scope,
            teacher_id=filters.get("teacher_id"),
            module_id=filters.get("module_id"),
            method=filters.get("method"),
            payment_type=filters.get("payment_type"),
            date_from=self._parse_date(filters.get("date_from")),
            date_to=self._parse_date(filters.get("date_to")),
            page=filters.get("page", 1),
            page_size=filters.get("page_size", 20),
            sort_by=filters.get("sort_by", "recorded_at"),
            sort_order=filters.get("sort_order", "desc"),
        )

        # Summary uses same filters — no separate endpoint
        summary = await self._repo.get_summary(
            branch_ids_scope=branch_ids_scope,
            branch_id=filters.get("branch_id"),
            teacher_id=filters.get("teacher_id"),
            module_id=filters.get("module_id"),
            method=filters.get("method"),
            payment_type=filters.get("payment_type"),
            date_from=self._parse_date(filters.get("date_from")),
            date_to=self._parse_date(filters.get("date_to")),
        )

        items = []
        for p in payments:
            items.append(
                (await _build_payment_response(p, self._session)).model_dump(by_alias=True)
            )

        return {
            "items": items,
            "pagination": build_pagination(
                filters.get("page", 1),
                filters.get("page_size", 20),
                total,
            ),
            "summary": PaymentSummary(**summary).model_dump(by_alias=True),
        }

    async def get_payment(self, payment_id: int, actor: User) -> dict:
        payment = await self._repo.get_by_id(payment_id)
        if not payment:
            from src.core.exceptions import ResourceNotFound
            raise ResourceNotFound(message="Payment not found.")
        return (await _build_payment_response(payment, self._session)).model_dump(by_alias=True)
