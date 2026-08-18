from datetime import date
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.common.pagination import build_pagination
from src.common.session_generator import generate_sessions
from src.modules.audit.service import log_action
from src.modules.config.service import ConfigService
from src.modules.groups.models import Group
from src.modules.groups.repository import GroupRepository
from src.modules.sessions.exceptions import SessionNotFound, DateRangeTooWide, SessionHasAttendance
from src.modules.sessions.models import Session
from src.modules.sessions.repository import SessionRepository
from src.modules.sessions.schemas import SessionResponse
from src.modules.users.models import User
from src.modules.classes.schemas import TeacherBasic


def _build_teacher(user) -> Optional[TeacherBasic]:
    if not user:
        return None
    return TeacherBasic(
        id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        avatar_url=user.avatar_url,
        default_commission_percent=float(user.default_commission_percent)
        if user.default_commission_percent is not None else None,
    )


def _build_response(sess: Session) -> SessionResponse:
    group = sess.group_
    cls = group.class_ if group else None
    mod = cls.module if cls else None
    teacher = group.teacher if (group and group.teacher_id) else (cls.teacher if cls else None)
    today = date.today()
    can_mark_attendance = (
        sess.status in ("scheduled", "completed") and sess.session_date <= today
    )
    can_request_reschedule = sess.status == "scheduled" and sess.session_date >= today

    return SessionResponse(
        id=sess.id,
        group_id=sess.group_id,
        group_name=group.name if group else "",
        class_id=cls.id if cls else 0,
        class_name=cls.name if cls else "",
        module_name=mod.name if mod else "",
        branch_id=sess.branch_id,
        branch_name=sess.branch.name if sess.branch else "",
        teacher=_build_teacher(teacher),
        session_date=sess.session_date,
        start_time=sess.start_time,
        end_time=sess.end_time,
        room=sess.room,
        status=sess.status,
        original_session_id=sess.original_session_id,
        notes=sess.notes,
        attendance_marked_at=sess.attendance_marked_at,
        attendance_marked_by=sess.attendance_marked_by,
        can_mark_attendance=can_mark_attendance,
        can_request_reschedule=can_request_reschedule,
        can_direct_reschedule=can_request_reschedule,
        created_at=sess.created_at,
        updated_at=sess.updated_at,
    )


class SessionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = SessionRepository(session)
        self._group_repo = GroupRepository(session)
        self._config_svc = ConfigService(session)

    def _get_branch_scope(self, actor: User) -> Optional[list[int]]:
        if actor.role == "admin":
            return [ub.branch_id for ub in (actor.branch_links or [])]
        return None

    async def _is_teacher_session(self, sess: Session, actor: User) -> bool:
        if actor.role != "teacher":
            return False
        group = sess.group_
        if not group:
            group_result = await self._session.execute(
                select(Group).where(Group.id == sess.group_id)
            )
            group = group_result.scalar_one_or_none()
        if not group:
            return False
        cls = group.class_
        if not cls:
            from src.modules.classes.models import Class

            class_result = await self._session.execute(
                select(Class).where(Class.id == group.class_id)
            )
            cls = class_result.scalar_one_or_none()
        effective_teacher = group.teacher_id or (cls.teacher_id if cls else None)
        return effective_teacher == actor.id

    async def _assert_session_access(self, sess: Session, actor: User) -> None:
        if actor.role in ("owner", "superAdmin"):
            return
        if actor.role == "admin":
            branch_ids_scope = self._get_branch_scope(actor)
            if branch_ids_scope is not None and sess.branch_id in branch_ids_scope:
                return
        if await self._is_teacher_session(sess, actor):
            return
        from src.core.exceptions import PermissionDenied
        raise PermissionDenied()

    async def list_sessions(self, params: dict, actor: User) -> dict:
        branch_ids_scope = self._get_branch_scope(actor)

        # 403 check: scoped caller must only request branches they own
        branch_id = params.get("branch_id")
        branch_ids = params.get("branch_ids")
        if actor.role == "admin" and branch_ids_scope is not None:
            if branch_id and branch_id not in branch_ids_scope:
                from src.core.exceptions import ForbiddenBranch
                raise ForbiddenBranch()
            if branch_ids and not set(branch_ids).issubset(set(branch_ids_scope)):
                from src.core.exceptions import ForbiddenBranch
                raise ForbiddenBranch()
        
        from_date = params.get("from_date")
        to_date = params.get("to_date")
        if from_date and to_date:
            if (to_date - from_date).days > 62:
                raise DateRangeTooWide()

        teacher_id = params.get("teacher_id")
        if actor.role == "teacher":
            teacher_id = actor.id
                
        sessions, total = await self._repo.get_all(
            group_id=params.get("group_id"),
            branch_id=branch_id,
            branch_ids=branch_ids,
            teacher_id=teacher_id,
            room=params.get("room"),
            from_date=params.get("from_date"),
            to_date=params.get("to_date"),
            status=params.get("status"),
            page=params.get("page", 1),
            page_size=params.get("page_size", 20),
            branch_ids_scope=branch_ids_scope,
        )
        items = [_build_response(s).model_dump(by_alias=True) for s in sessions]
        
        teachers = {}
        rooms = set()
        groups = {}
        for s in sessions:
            teacher = None
            if s.group_:
                teacher = s.group_.teacher
                if not teacher and s.group_.class_ and s.group_.class_.teacher:
                    teacher = s.group_.class_.teacher
            if teacher:
                teachers[teacher.id] = f"{teacher.first_name} {teacher.last_name}"
            if s.room:
                rooms.add(s.room)
            if s.group_:
                groups[s.group_.id] = s.group_.name

        return {
            "items": items,
            "pagination": build_pagination(params.get("page", 1), params.get("page_size", 20), total),
            "filters": {
                "teachers": [{"id": k, "name": v} for k, v in teachers.items()],
                "rooms": list(rooms),
                "groups": [{"id": k, "name": v} for k, v in groups.items()],
            }
        }

    async def get_session(self, session_id: int, actor: User) -> dict:
        sess = await self._repo.get_by_id(session_id)
        if not sess:
            raise SessionNotFound()
        branch_ids_scope = self._get_branch_scope(actor)
        if branch_ids_scope is not None and sess.branch_id not in branch_ids_scope:
            from src.core.exceptions import ForbiddenBranch
            raise ForbiddenBranch()
        if actor.role == "teacher" and not await self._is_teacher_session(sess, actor):
            from src.core.exceptions import PermissionDenied
            raise PermissionDenied()
        return _build_response(sess).model_dump(by_alias=True)

    async def update_session(self, session_id: int, data: dict, actor: User, ip: Optional[str] = None) -> dict:
        sess = await self._repo.get_by_id(session_id)
        if not sess:
            raise SessionNotFound()
        branch_ids_scope = self._get_branch_scope(actor)
        if branch_ids_scope is not None and sess.branch_id not in branch_ids_scope:
            from src.core.exceptions import ForbiddenBranch
            raise ForbiddenBranch()
        if actor.role == "teacher" and not await self._is_teacher_session(sess, actor):
            from src.core.exceptions import PermissionDenied
            raise PermissionDenied()

        changed = []
        for field in ("session_date", "start_time", "end_time", "room", "status", "notes"):
            if field in data and data[field] is not None:
                setattr(sess, field, data[field])
                changed.append(field)

        sess = await self._repo.save(sess)
        await log_action(
            self._session, user_id=actor.id, action="SESSION_UPDATED",
            category="academic", entity_type="session", entity_id=session_id,
            metadata={"changedFields": changed}, ip_address=ip,
        )
        sess = await self._repo.get_by_id(session_id)
        return _build_response(sess).model_dump(by_alias=True)

    async def delete_session(self, session_id: int, actor: User, ip: Optional[str] = None) -> None:
        sess = await self._repo.get_by_id(session_id)
        if not sess:
            raise SessionNotFound()
        branch_ids_scope = self._get_branch_scope(actor)
        if branch_ids_scope is not None and sess.branch_id not in branch_ids_scope:
            from src.core.exceptions import ForbiddenBranch
            raise ForbiddenBranch()
        
        if await self._repo.has_attendance(session_id):
            raise SessionHasAttendance()
        
        await log_action(
            self._session, user_id=actor.id, action="SESSION_DELETED",
            category="academic", entity_type="session", entity_id=session_id,
            metadata={"date": str(sess.session_date), "start": str(sess.start_time)},
            ip_address=ip,
        )
        await self._repo.delete(sess)
