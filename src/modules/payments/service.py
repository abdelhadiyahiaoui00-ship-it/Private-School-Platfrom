from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
import logging

from src.modules.auth.dependencies import CurrentUser
from src.modules.users.models import User
from src.modules.payments.models import Payment
from src.modules.payments.repository import PaymentRepository
from src.modules.payments.schemas import PaymentResponse

logger = logging.getLogger(__name__)


class PaymentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.pay_repo = PaymentRepository(session)

    async def get_payment(self, payment_id: int, actor: User) -> dict:
        payment = await self.pay_repo.get_by_id(payment_id)
        if not payment:
            from src.core.exceptions import ResourceNotFound
            raise ResourceNotFound(message="Payment not found")

        res = self._map_to_response(payment)
        return res.model_dump(by_alias=True)

    async def list_payments(self, filters: dict, actor: User) -> dict:
        branch_ids_scope = await self._get_actor_branch_scope(actor)
        
        date_from = filters.get("date_from")
        if isinstance(date_from, str):
            date_from = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
            
        date_to = filters.get("date_to")
        if isinstance(date_to, str):
            date_to = datetime.fromisoformat(date_to.replace('Z', '+00:00'))

        payments, total = await self.pay_repo.get_all(
            search=filters.get("search"),
            branch_id=filters.get("branch_id"),
            branch_ids_scope=branch_ids_scope,
            teacher_id=filters.get("teacher_id"),
            module_id=filters.get("module_id"),
            method=filters.get("method"),
            payment_type=filters.get("payment_type"),
            date_from=date_from,
            date_to=date_to,
            page=filters.get("page", 1),
            page_size=filters.get("page_size", 20),
            sort_by=filters.get("sort_by", "recorded_at"),
            sort_order=filters.get("sort_order", "desc"),
        )
        
        items = [self._map_to_response(p).model_dump(by_alias=True) for p in payments]

        return {
            "items": items,
            "total": total,
            "page": filters.get("page", 1),
            "pageSize": filters.get("page_size", 20),
        }

    async def get_summary(self, filters: dict, actor: User) -> dict:
        branch_ids_scope = await self._get_actor_branch_scope(actor)
        
        date_from = filters.get("date_from")
        if isinstance(date_from, str):
            date_from = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
            
        date_to = filters.get("date_to")
        if isinstance(date_to, str):
            date_to = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
            
        summary = await self.pay_repo.get_summary(
            branch_ids_scope=branch_ids_scope,
            branch_id=filters.get("branch_id"),
            teacher_id=filters.get("teacher_id"),
            module_id=filters.get("module_id"),
            method=filters.get("method"),
            payment_type=filters.get("payment_type"),
            date_from=date_from,
            date_to=date_to,
        )
        return summary

    async def _get_actor_branch_scope(self, actor: User) -> Optional[list[int]]:
        if actor.role in ("owner", "superAdmin"):
            return None
        return [b.branch_id for b in actor.branches]

    def _map_to_response(self, payment: Payment) -> PaymentResponse:
        return PaymentResponse(
            id=payment.id,
            subscription_id=payment.subscription_id,
            enrollment_id=payment.enrollment_id,
            student_id=payment.student_id,
            student={
                "id": payment.student.id if payment.student else payment.student_id,
                "first_name": payment.student.first_name if payment.student else "",
                "last_name": payment.student.last_name if payment.student else "",
                "avatar_url": payment.student.avatar_url if payment.student else None,
                "date_of_birth": payment.student.date_of_birth if payment.student else None,
            },
            branch_id=payment.branch_id,
            branch_name="Branch",  # In a full impl, we'd join branch or cache it
            class_id=payment.class_id,
            module_id=payment.module_id,
            module_name="Module",  # Similarly, would need a join if strictly required
            teacher_id=payment.teacher_id,
            teacher={
                "id": payment.teacher.id if payment.teacher else 0,
                "first_name": payment.teacher.first_name if payment.teacher else "",
                "last_name": payment.teacher.last_name if payment.teacher else "",
                "avatar_url": payment.teacher.avatar_url if payment.teacher else None,
                "default_commission_percent": payment.teacher.default_commission_percent if payment.teacher else None,
            } if payment.teacher else None,
            amount=payment.amount,
            currency=payment.currency,
            method=payment.method,
            commission_percent=payment.commission_percent,
            commission_amount=payment.commission_amount,
            net_amount=payment.net_amount,
            payment_type=payment.payment_type,
            recorded_by=payment.recorded_by,
            recorded_by_name=f"{payment.recorder.first_name} {payment.recorder.last_name}" if payment.recorder else "",
            recorded_at=payment.recorded_at,
            notes=payment.notes,
        )
