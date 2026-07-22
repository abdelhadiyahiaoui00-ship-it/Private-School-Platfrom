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
from src.modules.sessions.exceptions import SessionNotFound
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

    return SessionResponse(
        id=sess.id,
        group_id=sess.group_id,
        group_name=group.name if group else "",
        class_id=cls.id if cls else 0,
        class_name=cls.name if cls else "",
        module_name=mod.name if mod else "",
        branch_id=sess.branch_id,
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

    async def list_sessions(self, params: dict, actor: User) -> dict:
        branch_ids_scope = self._get_branch_scope(actor)
        sessions, total = await self._repo.get_all(
            group_id=params.get("group_id"),
            branch_id=params.get("branch_id"),
            teacher_id=params.get("teacher_id"),
            room=params.get("room"),
            from_date=params.get("from_date"),
            to_date=params.get("to_date"),
            status=params.get("status"),
            page=params.get("page", 1),
            page_size=params.get("page_size", 20),
            branch_ids_scope=branch_ids_scope,
        )
        items = [_build_response(s).model_dump(by_alias=True) for s in sessions]
        return {
            "items": items,
            "pagination": build_pagination(params.get("page", 1), params.get("page_size", 20), total),
        }

    async def get_session(self, session_id: int, actor: User) -> dict:
        sess = await self._repo.get_by_id(session_id)
        if not sess:
            raise SessionNotFound()
        branch_ids_scope = self._get_branch_scope(actor)
        if branch_ids_scope is not None and sess.branch_id not in branch_ids_scope:
            from src.core.exceptions import ForbiddenBranch
            raise ForbiddenBranch()
        return _build_response(sess).model_dump(by_alias=True)

    async def trigger_generation(self, group_id: int, from_date: date, weeks_ahead: Optional[int], actor: User, ip: Optional[str] = None) -> dict:
        group = await self._group_repo.get_by_id(group_id)
        if not group:
            from src.modules.groups.exceptions import GroupNotFound
            raise GroupNotFound()
        
        branch_ids_scope = self._get_branch_scope(actor)
        if branch_ids_scope is not None and group.class_.branch_id not in branch_ids_scope:
            from src.core.exceptions import ForbiddenBranch
            raise ForbiddenBranch()

        if not weeks_ahead:
            config = await self._config_svc.get_config()
            weeks_ahead = config.get("sessionGenerationHorizonWeeks", 8)

        # Generate sessions
        new_sessions, actual_until = await generate_sessions(
            self._session, group, from_date, weeks_ahead, group.class_.period_end
        )

        group.last_generated_until = actual_until
        await self._group_repo.save(group)

        await log_action(
            self._session, user_id=actor.id, action="SESSIONS_GENERATED",
            category="academic", entity_type="group", entity_id=group.id,
            metadata={"generatedCount": len(new_sessions), "until": str(actual_until)},
            ip_address=ip,
        )

        truncated = group.class_.period_end is not None and group.class_.period_end == actual_until
        return {
            "generatedCount": len(new_sessions),
            "generatedUntil": actual_until,
            "truncatedByPeriodEnd": truncated,
        }

    async def update_session(self, session_id: int, data: dict, actor: User, ip: Optional[str] = None) -> dict:
        sess = await self._repo.get_by_id(session_id)
        if not sess:
            raise SessionNotFound()
        branch_ids_scope = self._get_branch_scope(actor)
        if branch_ids_scope is not None and sess.branch_id not in branch_ids_scope:
            from src.core.exceptions import ForbiddenBranch
            raise ForbiddenBranch()

        changed = []
        for field in ("session_date", "start_time", "end_time", "room", "status", "notes"):
            if field in data:
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
        
        await log_action(
            self._session, user_id=actor.id, action="SESSION_DELETED",
            category="academic", entity_type="session", entity_id=session_id,
            metadata={"date": str(sess.session_date), "start": str(sess.start_time)},
            ip_address=ip,
        )
        await self._repo.delete(sess)
