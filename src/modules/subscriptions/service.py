from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
import logging

from src.common.financial import compute_financials, resolve_effective_commission
from src.common.pagination import build_pagination
from src.modules.audit.service import log_action
from src.modules.auth.dependencies import CurrentUser
from src.modules.users.models import User
from src.modules.subscriptions.models import Subscription
from src.modules.subscriptions.repository import SubscriptionRepository
from src.modules.payments.models import Payment
from src.modules.payments.repository import PaymentRepository
from src.modules.groups.repository import GroupRepository
from src.modules.classes.repository import ClassRepository
from src.modules.enrollments.repository import EnrollmentRepository
from src.modules.users.repository import UserRepository
from src.modules.config.service import ConfigService
from src.modules.subscriptions.exceptions import (
    SubscriptionNotFound,
    InvalidExtensionTarget,
    InvalidExtensionAmount,
    NoActiveSubscriptionsToExtend,
    SubscriptionAlreadyCancelled,
)
from src.modules.subscriptions.schemas import SubscriptionResponse, SubscriptionDetailResponse
from src.modules.payments.schemas import PaymentResponse
from src.core.error_codes import ErrorCode

logger = logging.getLogger(__name__)


class SubscriptionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.sub_repo = SubscriptionRepository(session)
        self.pay_repo = PaymentRepository(session)
        self.group_repo = GroupRepository(session)
        self.class_repo = ClassRepository(session)
        self.enroll_repo = EnrollmentRepository(session)
        self.user_repo = UserRepository(session)
        self.config_repo = ConfigService(session)
        # Audit service not needed as class

    async def get_subscription(self, sub_id: int, actor: User) -> dict:
        sub = await self.sub_repo.get_by_id(sub_id)
        if not sub:
            raise SubscriptionNotFound()
        
        enroll = await self.enroll_repo.get_by_id(sub.enrollment_id)
        enroll_source = enroll.source if enroll else "admin"

        is_latest = True
        latest_subs = await self.sub_repo.get_latest_subscription_ids([sub.enrollment_id])
        if latest_subs.get(sub.enrollment_id) != sub.id:
            is_latest = False

        res = self._map_to_detail_response(sub, is_latest, enroll_source)
        return res.model_dump(by_alias=True)

    async def list_subscriptions(self, filters: dict, actor: User) -> dict:
        branch_ids_scope = await self._get_actor_branch_scope(actor)
        subs, total = await self.sub_repo.get_all(
            search=filters.get("search"),
            branch_id=filters.get("branch_id"),
            branch_ids_scope=branch_ids_scope,
            group_id=filters.get("group_id"),
            class_id=filters.get("class_id"),
            module_id=filters.get("module_id"),
            teacher_id=filters.get("teacher_id"),
            type_=filters.get("type"),
            status=filters.get("status", "active"),
            expiring_soon_only=filters.get("expiring_soon_only", False),
            expired_only=filters.get("expired_only", False),
            page=filters.get("page", 1),
            page_size=filters.get("page_size", 20),
            sort_by=filters.get("sort_by", "created_at"),
            sort_order=filters.get("sort_order", "desc"),
        )
        
        enrollment_ids = [s.enrollment_id for s in subs]
        latest_map = await self.sub_repo.get_latest_subscription_ids(enrollment_ids)
        
        items = []
        for sub in subs:
            is_latest = latest_map.get(sub.enrollment_id) == sub.id
            items.append(self._map_to_response(sub, is_latest).model_dump(by_alias=True))

        stats = await self.sub_repo.get_stats(branch_ids_scope=branch_ids_scope)

        return {
            "items": items,
            "pagination": build_pagination(
                filters.get("page", 1),
                filters.get("page_size", 20),
                total,
            ),
            "stats": stats,
        }

    async def renew_subscription(self, sub_id: int, payload: dict, actor: User, ip: str = None) -> dict:
        # A renewal is basically extending an existing subscription for a new period
        # It creates a NEW Subscription record and a NEW Payment record.
        # This mirrors the confirm_payment logic but for an existing active/expired sub.
        
        old_sub = await self.sub_repo.get_by_id(sub_id)
        if not old_sub:
            raise SubscriptionNotFound()
            
        if old_sub.status == "cancelled":
            raise SubscriptionAlreadyCancelled()
            
        group = await self.group_repo.get_by_id(old_sub.group_id)
        cls = await self.class_repo.get_by_id(old_sub.group_id) # Using group's class_id
        if group:
            cls = await self.class_repo.get_by_id(group.class_id)
        
        amount = Decimal(str(payload["amount"]))
        if amount <= 0:
            from src.modules.subscriptions.exceptions import AmountMustBePositive
            raise AmountMustBePositive()

        # Get config
        sys_config = await self.config_repo.get()
        
        # Financials
        teacher = await self.user_repo.get_by_id(old_sub.teacher_id) if old_sub.teacher_id else None
        eff_comm_pct = resolve_effective_commission(cls, teacher)
        comm_amt, net_amt = compute_financials(amount, eff_comm_pct)

        # Dates / Sessions
        start_date = payload.get("start_date")
        duration_days = payload.get("duration_days")
        total_sessions = payload.get("total_sessions")
        
        sub_type = "monthly" if not group or group.subscription_type == "monthly" else "session_based"
        end_date = None
        rem_sessions = None

        if sub_type == "monthly":
            if not start_date:
                start_date = date.today()
            else:
                if isinstance(start_date, str):
                    start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            if not duration_days:
                duration_days = sys_config.monthly_default_duration_days
            end_date = start_date + timedelta(days=duration_days)
        else:
            if not total_sessions:
                total_sessions = group.session_count if group else 4
            rem_sessions = total_sessions

        # Terminate old subscription implicitly if not expired? No, the new one supersedes it.
        # Create new sub
        new_sub = Subscription(
            enrollment_id=old_sub.enrollment_id,
            student_id=old_sub.student_id,
            group_id=old_sub.group_id,
            branch_id=old_sub.branch_id,
            teacher_id=old_sub.teacher_id,
            module_id=old_sub.module_id,
            type=sub_type,
            status="active",
            price=float(amount),
            commission_percent=float(eff_comm_pct),
            commission_amount=float(comm_amt),
            net_amount=float(net_amt),
            start_date=start_date if sub_type == "monthly" else None,
            end_date=end_date,
            total_sessions=total_sessions if sub_type == "session_based" else None,
            remaining_sessions=rem_sessions,
            extension_log=[],
            activated_at=datetime.now(timezone.utc),
        )
        new_sub = await self.sub_repo.create(new_sub)

        # Create payment
        payment = Payment(
            subscription_id=new_sub.id,
            enrollment_id=old_sub.enrollment_id,
            student_id=old_sub.student_id,
            branch_id=old_sub.branch_id,
            class_id=cls.id if cls else None,
            module_id=old_sub.module_id,
            teacher_id=old_sub.teacher_id,
            amount=float(amount),
            currency="DZD",
            method=payload.get("method", "cash"),
            commission_percent=float(eff_comm_pct),
            commission_amount=float(comm_amt),
            net_amount=float(net_amt),
            payment_type="renewal",
            notes=payload.get("notes"),
            recorded_by=actor.id,
        )
        payment = await self.pay_repo.create(payment)
        
        # Load relationships
        new_sub = await self.sub_repo.get_by_id(new_sub.id)

        await log_action(
            session=self.session,
            user_id=actor.id,
            action="subscription_renew",
            category="subscriptions",
            entity_type="subscriptions",
            entity_id=new_sub.id,
            branch_id=old_sub.branch_id,
            metadata={"old_sub_id": old_sub.id, "amount": float(amount)},
            ip_address=ip,
        )

        enroll = await self.enroll_repo.get_by_id(old_sub.enrollment_id)
        enroll_source = enroll.source if enroll else "admin"

        res = self._map_to_detail_response(new_sub, is_latest=True, enroll_source=enroll_source)
        return res.model_dump(by_alias=True)

    async def extend_subscription(self, sub_id: int, payload: dict, actor: User, ip: str = None) -> dict:
        sub = await self.sub_repo.get_by_id(sub_id)
        if not sub:
            raise SubscriptionNotFound()
        if sub.status == "cancelled":
            raise SubscriptionAlreadyCancelled()
            
        days_to_add = payload.get("days_to_add")
        sessions_to_add = payload.get("sessions_to_add")
        reason = payload.get("reason", "")
        session_id = payload.get("session_id")
        
        if sub.type == "monthly":
            if not days_to_add:
                raise InvalidExtensionTarget()
            if days_to_add <= 0:
                raise InvalidExtensionAmount()
                
            if sub.end_date:
                sub.end_date = sub.end_date + timedelta(days=days_to_add)
            
            entry = {
                "date": datetime.now(timezone.utc).isoformat(),
                "daysAdded": days_to_add,
                "reason": reason,
                "appliedBy": actor.id,
                "appliedByName": f"{actor.first_name} {actor.last_name}",
                "sessionId": session_id,
            }
            
        else:
            if not sessions_to_add:
                raise InvalidExtensionTarget()
            if sessions_to_add <= 0:
                raise InvalidExtensionAmount()
                
            if sub.remaining_sessions is not None:
                sub.remaining_sessions += sessions_to_add
            if sub.total_sessions is not None:
                sub.total_sessions += sessions_to_add
                
            entry = {
                "date": datetime.now(timezone.utc).isoformat(),
                "sessionsAdded": sessions_to_add,
                "reason": reason,
                "appliedBy": actor.id,
                "appliedByName": f"{actor.first_name} {actor.last_name}",
                "sessionId": session_id,
            }
            
        # Append to json array - need to make a copy to trigger update
        log = list(sub.extension_log) if sub.extension_log else []
        log.append(entry)
        sub.extension_log = log
        
        sub = await self.sub_repo.save(sub)

        await log_action(
            session=self.session,
            user_id=actor.id,
            action="subscription_extend",
            category="subscriptions",
            entity_type="subscriptions",
            entity_id=sub.id,
            branch_id=sub.branch_id,
            metadata=entry,
            ip_address=ip,
        )

        is_latest = True # approximation
        res = self._map_to_response(sub, is_latest)
        return res.model_dump(by_alias=True)

    async def get_bulk_extend_preview(self, group_id: int, actor: User) -> dict:
        subs = await self.sub_repo.get_active_for_group(group_id)
        if not subs:
            return {"activeCount": 0, "monthlyCount": 0, "sessionBasedCount": 0}
            
        monthly = sum(1 for s in subs if s.type == "monthly")
        session_based = sum(1 for s in subs if s.type == "session_based")
        return {
            "activeCount": len(subs),
            "monthlyCount": monthly,
            "sessionBasedCount": session_based
        }

    async def apply_bulk_extend(self, group_id: int, payload: dict, actor: User, ip: str = None) -> dict:
        subs = await self.sub_repo.get_active_for_group(group_id)
        if not subs:
            raise NoActiveSubscriptionsToExtend()
            
        days_to_add = payload.get("days_to_add")
        sessions_to_add = payload.get("sessions_to_add")
        reason = payload.get("reason", "")
        session_id = payload.get("session_id")
        
        extended_count = 0
        for sub in subs:
            try:
                if sub.type == "monthly":
                    if not days_to_add or days_to_add <= 0:
                        continue
                    if sub.end_date:
                        sub.end_date = sub.end_date + timedelta(days=days_to_add)
                    entry = {
                        "date": datetime.now(timezone.utc).isoformat(),
                        "daysAdded": days_to_add,
                        "reason": reason,
                        "appliedBy": actor.id,
                        "appliedByName": f"{actor.first_name} {actor.last_name}",
                        "sessionId": session_id,
                    }
                else:
                    if not sessions_to_add or sessions_to_add <= 0:
                        continue
                    if sub.remaining_sessions is not None:
                        sub.remaining_sessions += sessions_to_add
                    if sub.total_sessions is not None:
                        sub.total_sessions += sessions_to_add
                    entry = {
                        "date": datetime.now(timezone.utc).isoformat(),
                        "sessionsAdded": sessions_to_add,
                        "reason": reason,
                        "appliedBy": actor.id,
                        "appliedByName": f"{actor.first_name} {actor.last_name}",
                        "sessionId": session_id,
                    }
                
                log = list(sub.extension_log) if sub.extension_log else []
                log.append(entry)
                sub.extension_log = log
                await self.sub_repo.save(sub)
                extended_count += 1
            except Exception as e:
                logger.error(f"Failed to extend sub {sub.id}: {e}")
                
        await log_action(
            session=self.session,
            user_id=actor.id,
            action="group_bulk_extend",
            category="subscriptions",
            entity_type="groups",
            entity_id=group_id,
            metadata={"extended_count": extended_count, "reason": reason},
            ip_address=ip,
        )

        return {"extendedCount": extended_count}

    async def cancel_subscription(self, sub_id: int, payload: dict, actor: User, ip: str = None) -> dict:
        sub = await self.sub_repo.get_by_id(sub_id)
        if not sub:
            raise SubscriptionNotFound()
            
        if sub.status == "cancelled":
            raise SubscriptionAlreadyCancelled()
            
        sub.status = "cancelled"
        sub.cancelled_at = datetime.now(timezone.utc)
        sub.cancelled_reason = payload.get("reason")
        
        sub = await self.sub_repo.save(sub)

        await log_action(
            session=self.session,
            user_id=actor.id,
            action="subscription_cancel",
            category="subscriptions",
            entity_type="subscriptions",
            entity_id=sub.id,
            branch_id=sub.branch_id,
            metadata={"reason": sub.cancelled_reason},
            ip_address=ip,
        )

        is_latest = True # approximation
        res = self._map_to_response(sub, is_latest)
        return res.model_dump(by_alias=True)
        
    async def confirm_payment_for_enrollment(self, enrollment_id: int, payload: dict, actor: User, ip: str = None) -> dict:
        enroll = await self.enroll_repo.get_by_id(enrollment_id)
        if not enroll:
            from src.core.exceptions import ResourceNotFound
            raise ResourceNotFound(message="Enrollment not found")
            
        if enroll.status != "pending":
            from src.modules.subscriptions.exceptions import EnrollmentNotPending
            raise EnrollmentNotPending()
            
        group = await self.group_repo.get_by_id(enroll.group_id)
        cls = await self.class_repo.get_by_id(group.class_id) if group else None
        
        amount = Decimal(str(payload["amount"]))
        if amount <= 0:
            from src.modules.subscriptions.exceptions import AmountMustBePositive
            raise AmountMustBePositive()

        sys_config = await self.config_repo.get()
        
        # Determine teacher and module
        teacher_id = cls.teacher_id if cls else None
        teacher = await self.user_repo.get_by_id(teacher_id) if teacher_id else None
        module_id = cls.module_id if cls else None
        
        # Financials
        eff_comm_pct = resolve_effective_commission(cls, teacher)
        comm_amt, net_amt = compute_financials(amount, eff_comm_pct)

        # Dates / Sessions
        start_date = payload.get("start_date")
        duration_days = payload.get("duration_days")
        total_sessions = payload.get("total_sessions")
        
        sub_type = "monthly" if not group or group.subscription_type == "monthly" else "session_based"
        end_date = None
        rem_sessions = None

        if sub_type == "monthly":
            if not start_date:
                start_date = date.today()
            else:
                if isinstance(start_date, str):
                    start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            if not duration_days:
                duration_days = sys_config.monthly_default_duration_days
            end_date = start_date + timedelta(days=duration_days)
        else:
            if not total_sessions:
                total_sessions = group.session_count if group else 4
            rem_sessions = total_sessions

        student_id = enroll.student_id or payload.get("student_id") or enroll.enrolled_by or actor.id
        sub = Subscription(
            enrollment_id=enroll.id,
            student_id=student_id,
            group_id=enroll.group_id,
            branch_id=enroll.branch_id,
            teacher_id=teacher_id,
            module_id=module_id,
            type=sub_type,
            status="active",
            price=float(amount),
            commission_percent=float(eff_comm_pct),
            commission_amount=float(comm_amt),
            net_amount=float(net_amt),
            start_date=start_date if sub_type == "monthly" else None,
            end_date=end_date,
            total_sessions=total_sessions if sub_type == "session_based" else None,
            remaining_sessions=rem_sessions,
            extension_log=[],
            activated_at=datetime.now(timezone.utc),
        )
        sub = await self.sub_repo.create(sub)

        # Create Payment
        payment = Payment(
            subscription_id=sub.id,
            enrollment_id=enroll.id,
            student_id=student_id,
            branch_id=enroll.branch_id,
            class_id=cls.id if cls else None,
            module_id=module_id,
            teacher_id=teacher_id,
            amount=float(amount),
            currency="DZD",
            method=payload.get("method", "cash"),
            commission_percent=float(eff_comm_pct),
            commission_amount=float(comm_amt),
            net_amount=float(net_amt),
            payment_type="initial",
            notes=payload.get("notes"),
            recorded_by=actor.id,
        )
        payment = await self.pay_repo.create(payment)
        
        # Activate enrollment
        enroll.status = "active"
        enroll.activated_at = datetime.now(timezone.utc)
        enroll = await self.enroll_repo.save(enroll)
        
        # Load relationships
        sub = await self.sub_repo.get_by_id(sub.id)

        await log_action(
            session=self.session,
            user_id=actor.id,
            action="enrollment_confirm_payment",
            category="enrollments",
            entity_type="enrollments",
            entity_id=enroll.id,
            branch_id=enroll.branch_id,
            metadata={"sub_id": sub.id, "amount": float(amount)},
            ip_address=ip,
        )

        res = self._map_to_detail_response(sub, is_latest=True, enroll_source=enroll.source)
        return {"subscription": res.model_dump(by_alias=True)}


    async def _get_actor_branch_scope(self, actor: User) -> Optional[list[int]]:
        if actor.role in ("owner", "superAdmin"):
            return None
        return [b.branch_id for b in getattr(actor, "branch_links", [])]

    def _map_to_response(self, sub: Subscription, is_latest: bool) -> SubscriptionResponse:
        today = date.today()
        is_expiring_soon = False
        is_expired = False
        
        if sub.status == "active" and sub.end_date:
            if sub.end_date < today:
                is_expired = True
            elif sub.end_date <= today + timedelta(days=3):
                is_expiring_soon = True
                
        return SubscriptionResponse(
            id=sub.id,
            enrollment_id=sub.enrollment_id,
            student_id=sub.student_id,
            student={
                "id": sub.student.id if sub.student else sub.student_id,
                "first_name": sub.student.first_name if sub.student else "",
                "last_name": sub.student.last_name if sub.student else "",
                "avatar_url": sub.student.avatar_url if sub.student else None,
                "date_of_birth": sub.student.date_of_birth if sub.student else None,
            },
            group_id=sub.group_id,
            group_name=sub.group.name if sub.group else "",
            class_id=sub.group.class_.id if sub.group and sub.group.class_ else 0,
            class_name=sub.group.class_.name if sub.group and sub.group.class_ else "",
            module_id=sub.module_id or 0,
            module_name=sub.group.class_.module.name if sub.group and sub.group.class_ and sub.group.class_.module else "",
            branch_id=sub.branch_id,
            branch_name=sub.branch.name if getattr(sub, "branch", None) else "",
            teacher_id=sub.teacher_id or 0,
            teacher={
                "id": sub.teacher.id if sub.teacher else 0,
                "first_name": sub.teacher.first_name if sub.teacher else "",
                "last_name": sub.teacher.last_name if sub.teacher else "",
                "avatar_url": sub.teacher.avatar_url if sub.teacher else None,
                "default_commission_percent": sub.teacher.default_commission_percent if sub.teacher else None,
            },
            type=sub.type,
            status=sub.status,
            start_date=sub.start_date,
            end_date=sub.end_date,
            total_sessions=sub.total_sessions,
            remaining_sessions=sub.remaining_sessions,
            price=sub.price,
            commission_percent=sub.commission_percent,
            commission_amount=sub.commission_amount,
            net_amount=sub.net_amount,
            is_expiring_soon=is_expiring_soon,
            is_expired=is_expired,
            is_latest_for_enrollment=is_latest,
            extension_log=sub.extension_log or [],
            created_at=sub.created_at,
            updated_at=sub.updated_at,
            activated_at=sub.activated_at,
            cancelled_at=sub.cancelled_at,
            cancelled_reason=sub.cancelled_reason,
        )

    def _map_to_detail_response(self, sub: Subscription, is_latest: bool, enroll_source: str) -> SubscriptionDetailResponse:
        base = self._map_to_response(sub, is_latest)
        payment = None
        if sub.payment:
            payment = PaymentResponse(
                id=sub.payment.id,
                subscription_id=sub.id,
                enrollment_id=sub.payment.enrollment_id,
                student_id=sub.payment.student_id,
                student=base.student,
                branch_id=sub.payment.branch_id,
                branch_name=base.branch_name,
                class_id=sub.payment.class_id,
                module_id=sub.payment.module_id,
                module_name=base.module_name,
                teacher_id=sub.payment.teacher_id,
                teacher=base.teacher,
                amount=sub.payment.amount,
                currency=sub.payment.currency,
                method=sub.payment.method,
                commission_percent=sub.payment.commission_percent,
                commission_amount=sub.payment.commission_amount,
                net_amount=sub.payment.net_amount,
                payment_type=sub.payment.payment_type,
                recorded_by=sub.payment.recorded_by,
                recorded_by_name=f"{sub.payment.recorder.first_name} {sub.payment.recorder.last_name}" if sub.payment.recorder else "",
                recorded_at=sub.payment.recorded_at,
                notes=sub.payment.notes,
            )
            
        return SubscriptionDetailResponse(
            **base.model_dump(),
            payment=payment,
            enrollment_source=enroll_source,
        )
