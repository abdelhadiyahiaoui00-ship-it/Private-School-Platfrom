from datetime import date, datetime, time, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.common.pagination import build_pagination
from src.common.reschedule_engine import apply_reschedule
from src.modules.attendance.exceptions import (
    RescheduleRequestAlreadyPending,
    RescheduleRequestAlreadyResolved,
    RescheduleTargetInvalid,
    SessionNotReschedulable,
    SessionStatusInvalidForAction,
)
from src.modules.attendance.reschedule_schemas import RescheduleRequestResponse
from src.modules.audit.service import log_action
from src.modules.notifications.service import create_notification
from src.modules.sessions.models import Session
from src.modules.sessions.reschedule_models import SessionRescheduleRequest
from src.modules.users.models import User


def _parse_time(time_str: str) -> time:
    try:
        parts = time_str.split(":")
        return time(int(parts[0]), int(parts[1]))
    except (AttributeError, TypeError, ValueError):
        raise RescheduleTargetInvalid()


async def _build_request_response(
    req: SessionRescheduleRequest, db: AsyncSession
) -> RescheduleRequestResponse:
    requester_name = ""
    if req.requester:
        requester_name = f"{req.requester.first_name} {req.requester.last_name}"

    reviewer_name = None
    if req.reviewer:
        reviewer_name = f"{req.reviewer.first_name} {req.reviewer.last_name}"

    session_result = await db.execute(select(Session).where(Session.id == req.session_id))
    sess = session_result.scalar_one_or_none()
    session_dict = {}
    if sess:
        session_dict = {
            "id": sess.id,
            "sessionDate": str(sess.session_date),
            "startTime": str(sess.start_time)[:5],
            "endTime": str(sess.end_time)[:5],
            "room": sess.room,
            "status": sess.status,
        }

    return RescheduleRequestResponse(
        id=req.id,
        session_id=req.session_id,
        session=session_dict,
        requested_by=req.requested_by,
        requested_by_name=requester_name,
        reason=req.reason,
        proposed_date=req.proposed_date,
        proposed_start_time=str(req.proposed_start_time)[:5],
        proposed_end_time=str(req.proposed_end_time)[:5],
        proposed_room=req.proposed_room,
        status=req.status,
        reviewed_by=req.reviewed_by,
        reviewed_by_name=reviewer_name,
        reviewed_at=req.reviewed_at,
        rejection_reason=req.rejection_reason,
        created_at=req.created_at,
    )


async def _build_session_detail_dict(sess: Session, db: AsyncSession) -> dict:
    return {
        "id": sess.id,
        "sessionDate": str(sess.session_date),
        "startTime": str(sess.start_time)[:5],
        "endTime": str(sess.end_time)[:5],
        "room": sess.room,
        "status": sess.status,
        "originalSessionId": sess.original_session_id,
        "branchId": sess.branch_id,
        "groupId": sess.group_id,
    }


class RescheduleService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _get_branch_scope(self, actor: User) -> Optional[list[int]]:
        if actor.role in ("owner", "superAdmin"):
            return None
        if actor.role == "admin":
            return [link.branch_id for link in (actor.branch_links or [])]
        return None

    async def _get_session_or_404(self, session_id: int) -> Session:
        result = await self._session.execute(select(Session).where(Session.id == session_id))
        sess = result.scalar_one_or_none()
        if not sess:
            from src.core.exceptions import ResourceNotFound

            raise ResourceNotFound(message="Session not found.")
        return sess

    async def create_request(
        self, session_id: int, data: dict, actor: User, ip: Optional[str] = None
    ) -> dict:
        sess = await self._get_session_or_404(session_id)
        await self._assert_session_access(sess, actor)

        today = date.today()
        if sess.status != "scheduled" or sess.session_date < today:
            raise SessionNotReschedulable()

        start = _parse_time(data["proposed_start_time"])
        end = _parse_time(data["proposed_end_time"])
        if end <= start or data["proposed_date"] < today:
            raise RescheduleTargetInvalid()

        existing_result = await self._session.execute(
            select(SessionRescheduleRequest).where(
                SessionRescheduleRequest.session_id == session_id,
                SessionRescheduleRequest.status == "pending",
            )
        )
        if existing_result.scalar_one_or_none():
            raise RescheduleRequestAlreadyPending()

        req = SessionRescheduleRequest(
            session_id=session_id,
            requested_by=actor.id,
            reason=data["reason"],
            proposed_date=data["proposed_date"],
            proposed_start_time=start,
            proposed_end_time=end,
            proposed_room=data.get("proposed_room"),
            status="pending",
        )
        self._session.add(req)
        await self._session.flush()
        await self._session.refresh(req)

        from src.modules.users.models import User as UserModel, UserBranch

        admins_result = await self._session.execute(
            select(UserModel)
            .join(UserBranch, UserBranch.user_id == UserModel.id)
            .where(
                UserBranch.branch_id == sess.branch_id,
                UserModel.role.in_(["admin", "superAdmin", "owner"]),
                UserModel.status == "active",
            )
        )
        for admin in admins_result.scalars().all():
            perms = admin.permissions or {}
            if admin.role in ("superAdmin", "owner") or perms.get("manageSessions"):
                await create_notification(
                    self._session,
                    user_id=admin.id,
                    type="reschedule_request_submitted",
                    title="طلب إعادة جدولة جديد",
                    message=f"طلب تغيير موعد الحصة بتاريخ {sess.session_date}",
                    entity_type="session_reschedule_request",
                    entity_id=req.id,
                    actor_id=actor.id,
                )

        await log_action(
            self._session,
            user_id=actor.id,
            action="RESCHEDULE_REQUESTED",
            category="sessions",
            entity_type="session_reschedule_request",
            entity_id=req.id,
            metadata={"sessionId": session_id, "proposedDate": str(data["proposed_date"])},
            ip_address=ip,
        )

        req_result = await self._session.execute(
            select(SessionRescheduleRequest)
            .where(SessionRescheduleRequest.id == req.id)
            .options(
                selectinload(SessionRescheduleRequest.requester),
                selectinload(SessionRescheduleRequest.reviewer),
            )
        )
        req = req_result.scalar_one()
        return (await _build_request_response(req, self._session)).model_dump(by_alias=True)

    async def list_requests(self, params: dict, actor: User) -> dict:
        branch_scope = self._get_branch_scope(actor)
        filters = []

        if branch_scope is not None:
            filters.append(Session.branch_id.in_(branch_scope))
        if params.get("branch_id"):
            branch_id = params["branch_id"]
            if branch_scope is not None and branch_id not in branch_scope:
                from src.core.exceptions import ForbiddenBranch

                raise ForbiddenBranch()
            filters.append(Session.branch_id == branch_id)
        if params.get("teacher_id"):
            filters.append(SessionRescheduleRequest.requested_by == params["teacher_id"])
        if params.get("group_id"):
            filters.append(Session.group_id == params["group_id"])

        q = (
            select(SessionRescheduleRequest)
            .join(Session, Session.id == SessionRescheduleRequest.session_id)
            .options(
                selectinload(SessionRescheduleRequest.requester),
                selectinload(SessionRescheduleRequest.reviewer),
            )
        )
        if filters:
            q = q.where(*filters)

        status = params.get("status", "pending")
        if status and status != "all":
            q = q.where(SessionRescheduleRequest.status == status)

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self._session.execute(count_q)).scalar_one()

        page = params.get("page", 1)
        page_size = params.get("page_size", 20)
        q = q.order_by(SessionRescheduleRequest.created_at.desc())
        q = q.offset((page - 1) * page_size).limit(page_size)

        result = await self._session.execute(q)
        requests = result.scalars().all()

        stats_q = (
            select(SessionRescheduleRequest.status, func.count(SessionRescheduleRequest.id))
            .join(Session, Session.id == SessionRescheduleRequest.session_id)
            .group_by(SessionRescheduleRequest.status)
        )
        if filters:
            stats_q = stats_q.where(*filters)
        stats_result = await self._session.execute(stats_q)
        stats = {"pending": 0, "approved": 0, "rejected": 0}
        for status_value, count in stats_result.all():
            if status_value in stats:
                stats[status_value] = count

        items = [
            (await _build_request_response(req, self._session)).model_dump(by_alias=True)
            for req in requests
        ]
        return {
            "items": items,
            "pagination": build_pagination(page, page_size, total),
            "stats": stats,
        }

    async def approve_request(
        self, request_id: int, actor: User, ip: Optional[str] = None
    ) -> dict:
        req_result = await self._session.execute(
            select(SessionRescheduleRequest)
            .where(SessionRescheduleRequest.id == request_id)
            .options(
                selectinload(SessionRescheduleRequest.requester),
                selectinload(SessionRescheduleRequest.reviewer),
            )
        )
        req = req_result.scalar_one_or_none()
        if not req:
            from src.core.exceptions import ResourceNotFound

            raise ResourceNotFound(message="Reschedule request not found.")
        if req.status != "pending":
            raise RescheduleRequestAlreadyResolved()

        sess = await self._get_session_or_404(req.session_id)
        await self._assert_session_admin_access(sess, actor)

        old_session, new_session = await apply_reschedule(
            db=self._session,
            old_session=sess,
            new_date=req.proposed_date,
            new_start_time=req.proposed_start_time,
            new_end_time=req.proposed_end_time,
            new_room=req.proposed_room,
            actor_id=actor.id,
        )

        now = datetime.now(timezone.utc)
        req.status = "approved"
        req.reviewed_by = actor.id
        req.reviewed_at = now
        await self._session.flush()

        if req.requested_by:
            await create_notification(
                self._session,
                user_id=req.requested_by,
                type="reschedule_request_approved",
                title="تمت الموافقة على طلب إعادة الجدولة",
                message=f"سيتم إقامة الحصة يوم {req.proposed_date} الساعة {str(req.proposed_start_time)[:5]}",
                entity_type="session",
                entity_id=new_session.id,
                actor_id=actor.id,
            )

        await log_action(
            self._session,
            user_id=actor.id,
            action="RESCHEDULE_APPROVED",
            category="sessions",
            entity_type="session_reschedule_request",
            entity_id=request_id,
            metadata={"oldSessionId": old_session.id, "newSessionId": new_session.id},
            ip_address=ip,
        )

        return {
            "oldSession": await _build_session_detail_dict(old_session, self._session),
            "newSession": await _build_session_detail_dict(new_session, self._session),
        }

    async def reject_request(
        self, request_id: int, reason: str, actor: User, ip: Optional[str] = None
    ) -> dict:
        req_result = await self._session.execute(
            select(SessionRescheduleRequest)
            .where(SessionRescheduleRequest.id == request_id)
            .options(selectinload(SessionRescheduleRequest.requester))
        )
        req = req_result.scalar_one_or_none()
        if not req:
            from src.core.exceptions import ResourceNotFound

            raise ResourceNotFound(message="Reschedule request not found.")
        if req.status != "pending":
            raise RescheduleRequestAlreadyResolved()

        sess = await self._get_session_or_404(req.session_id)
        await self._assert_session_admin_access(sess, actor)

        now = datetime.now(timezone.utc)
        req.status = "rejected"
        req.reviewed_by = actor.id
        req.reviewed_at = now
        req.rejection_reason = reason
        await self._session.flush()

        if req.requested_by:
            await create_notification(
                self._session,
                user_id=req.requested_by,
                type="reschedule_request_rejected",
                title="تم رفض طلب إعادة الجدولة",
                message=reason,
                entity_type="session_reschedule_request",
                entity_id=request_id,
                actor_id=actor.id,
            )

        await log_action(
            self._session,
            user_id=actor.id,
            action="RESCHEDULE_REJECTED",
            category="sessions",
            entity_type="session_reschedule_request",
            entity_id=request_id,
            metadata={"reason": reason},
            ip_address=ip,
        )
        return {"rejected": True}

    async def direct_reschedule(
        self, session_id: int, data: dict, actor: User, ip: Optional[str] = None
    ) -> dict:
        sess = await self._get_session_or_404(session_id)
        await self._assert_session_admin_access(sess, actor)

        today = date.today()
        if sess.status != "scheduled" or sess.session_date < today:
            raise SessionNotReschedulable()

        new_start = _parse_time(data["new_start_time"])
        new_end = _parse_time(data["new_end_time"])
        if new_end <= new_start or data["new_date"] < today:
            raise RescheduleTargetInvalid()

        pending_result = await self._session.execute(
            select(SessionRescheduleRequest)
            .where(
                SessionRescheduleRequest.session_id == session_id,
                SessionRescheduleRequest.status == "pending",
            )
            .options(selectinload(SessionRescheduleRequest.requester))
        )
        pending_req = pending_result.scalar_one_or_none()
        if pending_req:
            now = datetime.now(timezone.utc)
            pending_req.status = "rejected"
            pending_req.reviewed_by = actor.id
            pending_req.reviewed_at = now
            pending_req.rejection_reason = "تم استبداله بإعادة جدولة مباشرة من الإدارة"
            await self._session.flush()
            if pending_req.requested_by:
                await create_notification(
                    self._session,
                    user_id=pending_req.requested_by,
                    type="reschedule_request_rejected",
                    title="تم رفض طلب إعادة الجدولة تلقائياً",
                    message="تم استبداله بإعادة جدولة مباشرة من الإدارة",
                    entity_type="session_reschedule_request",
                    entity_id=pending_req.id,
                    actor_id=actor.id,
                )

        old_session, new_session = await apply_reschedule(
            db=self._session,
            old_session=sess,
            new_date=data["new_date"],
            new_start_time=new_start,
            new_end_time=new_end,
            new_room=data.get("new_room"),
            actor_id=actor.id,
        )

        await log_action(
            self._session,
            user_id=actor.id,
            action="SESSION_RESCHEDULED_DIRECT",
            category="sessions",
            entity_type="session",
            entity_id=session_id,
            metadata={
                "oldSessionId": old_session.id,
                "newSessionId": new_session.id,
                "reason": data.get("reason"),
            },
            ip_address=ip,
        )

        return {
            "oldSession": await _build_session_detail_dict(old_session, self._session),
            "newSession": await _build_session_detail_dict(new_session, self._session),
        }

    async def mark_teacher_absent(
        self,
        session_id: int,
        reason: Optional[str],
        actor: User,
        ip: Optional[str] = None,
    ) -> dict:
        sess = await self._get_session_or_404(session_id)
        await self._assert_session_admin_access(sess, actor)

        if sess.status != "scheduled":
            raise SessionStatusInvalidForAction()

        sess.status = "teacher_absent"
        if reason:
            sess.notes = reason
        await self._session.flush()

        await log_action(
            self._session,
            user_id=actor.id,
            action="SESSION_MARKED_TEACHER_ABSENT",
            category="sessions",
            entity_type="session",
            entity_id=session_id,
            metadata={"reason": reason},
            ip_address=ip,
        )

        return {
            "id": sess.id,
            "status": sess.status,
            "notes": sess.notes,
            "sessionDate": str(sess.session_date),
            "groupId": sess.group_id,
        }

    async def _assert_session_access(self, session: Session, actor: User) -> None:
        if actor.role in ("owner", "superAdmin"):
            return
        if actor.role == "admin":
            perms = actor.permissions or {}
            if perms.get("manageSessions") and self._actor_has_branch(actor, session.branch_id):
                return
        if actor.role == "teacher":
            from src.modules.classes.models import Class as SchoolClass
            from src.modules.groups.models import Group

            group_result = await self._session.execute(
                select(Group).where(Group.id == session.group_id)
            )
            group = group_result.scalar_one_or_none()
            if group:
                class_result = await self._session.execute(
                    select(SchoolClass).where(SchoolClass.id == group.class_id)
                )
                cls = class_result.scalar_one_or_none()
                effective_teacher = group.teacher_id or (cls.teacher_id if cls else None)
                if effective_teacher == actor.id:
                    return

        from src.core.exceptions import PermissionDenied

        raise PermissionDenied()

    async def _assert_session_admin_access(self, session: Session, actor: User) -> None:
        if actor.role in ("owner", "superAdmin"):
            return
        if actor.role == "admin":
            perms = actor.permissions or {}
            if perms.get("manageSessions") and self._actor_has_branch(actor, session.branch_id):
                return

        from src.core.exceptions import PermissionDenied

        raise PermissionDenied()

    def _actor_has_branch(self, actor: User, branch_id: int) -> bool:
        return any(link.branch_id == branch_id for link in (actor.branch_links or []))
