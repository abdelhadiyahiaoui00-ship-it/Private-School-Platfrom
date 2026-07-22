from datetime import date
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.pagination import build_pagination
from src.modules.audit.service import log_action
from src.modules.classes.repository import ClassRepository
from src.modules.classes.schemas import TeacherBasic
from src.modules.groups.exceptions import (
    CannotChangeSubscriptionType, GroupHasActiveDependencies,
    GroupNotFound, InvalidScheduleFormat
)
from src.modules.groups.models import Group
from src.modules.groups.repository import GroupRepository
from src.modules.groups.schemas import GroupResponse
from src.modules.users.models import User


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


def _build_response(group: Group) -> GroupResponse:
    # Resolve teacher: group.teacher or group.class_.teacher
    teacher = group.teacher if group.teacher_id else (group.class_.teacher if group.class_ else None)
    return GroupResponse(
        id=group.id,
        class_id=group.class_id,
        class_name=group.class_.name if group.class_ else "",
        module_name=group.class_.module.name if (group.class_ and group.class_.module) else "",
        name=group.name,
        teacher=_build_teacher(teacher),
        schedule=group.schedule,
        room=group.room,
        max_students=group.max_students,
        price=float(group.price),
        subscription_type=group.subscription_type,
        session_count=group.session_count,
        status=group.status,
        last_generated_until=group.last_generated_until,
        created_at=group.created_at,
        updated_at=group.updated_at,
        active_enrollments=0,  # Sprint 5
        available_seats=group.max_students,  # Sprint 5
    )


class GroupService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = GroupRepository(session)
        self._class_repo = ClassRepository(session)

    def _get_branch_scope(self, actor: User) -> Optional[list[int]]:
        if actor.role == "admin":
            return [ub.branch_id for ub in (actor.branch_links or [])]
        return None

    async def _check_branch_access(self, class_id: int, actor: User) -> None:
        cls = await self._class_repo.get_by_id(class_id)
        if not cls:
            from src.modules.classes.exceptions import ClassNotFound
            raise ClassNotFound()
        branch_ids_scope = self._get_branch_scope(actor)
        if branch_ids_scope is not None and cls.branch_id not in branch_ids_scope:
            from src.core.exceptions import ForbiddenBranch
            raise ForbiddenBranch()

    async def list_groups(self, params: dict, actor: User) -> dict:
        branch_ids_scope = self._get_branch_scope(actor)
        groups, total = await self._repo.get_all(
            class_id=params.get("class_id"),
            branch_id=params.get("branch_id"),
            teacher_id=params.get("teacher_id"),
            status=params.get("status", "active"),
            page=params.get("page", 1),
            page_size=params.get("page_size", 20),
            branch_ids_scope=branch_ids_scope,
        )
        stats = await self._repo.get_stats(branch_ids_scope)
        items = [_build_response(g).model_dump(by_alias=True) for g in groups]
        return {
            "items": items,
            "pagination": build_pagination(params.get("page", 1), params.get("page_size", 20), total),
            "stats": stats,
        }

    async def get_group(self, group_id: int, actor: User) -> dict:
        group = await self._repo.get_by_id(group_id)
        if not group:
            raise GroupNotFound()
        await self._check_branch_access(group.class_id, actor)
        return _build_response(group).model_dump(by_alias=True)

    async def create_group(self, data: dict, actor: User, ip: Optional[str] = None) -> dict:
        await self._check_branch_access(data["class_id"], actor)
        if data.get("subscription_type") == "session_based" and not data.get("session_count"):
            raise InvalidScheduleFormat(message="session_count required for session_based groups.")
        if data.get("teacher_id"):
            cls = await self._class_repo.get_by_id(data["class_id"])
            if actor.role == "admin":
                if not await self._class_repo.teacher_assigned_to_branch(data["teacher_id"], cls.branch_id):
                    from src.modules.classes.exceptions import TeacherNotAssignedToBranch
                    raise TeacherNotAssignedToBranch()

        group = Group(
            class_id=data["class_id"],
            name=data["name"],
            teacher_id=data.get("teacher_id"),
            schedule=data["schedule"],
            room=data["room"],
            max_students=data["max_students"],
            price=data["price"],
            subscription_type=data["subscription_type"],
            session_count=data.get("session_count"),
            status="active",
        )
        group = await self._repo.create(group)
        await log_action(
            self._session, user_id=actor.id, action="GROUP_CREATED",
            category="academic", entity_type="group", entity_id=group.id,
            metadata={"classId": group.class_id, "name": group.name},
            ip_address=ip,
        )
        group = await self._repo.get_by_id(group.id)
        return _build_response(group).model_dump(by_alias=True)

    async def update_group(self, group_id: int, data: dict, actor: User, ip: Optional[str] = None) -> dict:
        group = await self._repo.get_by_id(group_id)
        if not group:
            raise GroupNotFound()
        await self._check_branch_access(group.class_id, actor)

        changed = []
        if "subscription_type" in data and data["subscription_type"] != group.subscription_type:
            if await self._repo.has_active_enrollments(group_id):
                raise CannotChangeSubscriptionType()
            group.subscription_type = data["subscription_type"]
            changed.append("subscription_type")
            if data["subscription_type"] == "session_based" and not data.get("session_count") and not group.session_count:
                raise InvalidScheduleFormat(message="session_count required for session_based groups.")

        for field in ("name", "teacher_id", "schedule", "room", "max_students", "price", "session_count"):
            if field in data:
                setattr(group, field, data[field])
                changed.append(field)

        group = await self._repo.save(group)
        await log_action(
            self._session, user_id=actor.id, action="GROUP_UPDATED",
            category="academic", entity_type="group", entity_id=group_id,
            metadata={"changedFields": changed}, ip_address=ip,
        )
        group = await self._repo.get_by_id(group_id)
        return _build_response(group).model_dump(by_alias=True)

    async def set_status(self, group_id: int, status: str, actor: User, ip: Optional[str] = None) -> dict:
        group = await self._repo.get_by_id(group_id)
        if not group:
            raise GroupNotFound()
        await self._check_branch_access(group.class_id, actor)
        group.status = status
        group = await self._repo.save(group)
        await log_action(
            self._session, user_id=actor.id, action="GROUP_UPDATED",
            category="academic", entity_type="group", entity_id=group_id,
            metadata={"changedFields": ["status"], "status": status},
            ip_address=ip,
        )
        group = await self._repo.get_by_id(group_id)
        return _build_response(group).model_dump(by_alias=True)

    async def delete_group(self, group_id: int, actor: User, ip: Optional[str] = None) -> None:
        group = await self._repo.get_by_id(group_id)
        if not group:
            raise GroupNotFound()
        await self._check_branch_access(group.class_id, actor)
        if await self._repo.has_any_dependencies(group_id):
            raise GroupHasActiveDependencies()
        await log_action(
            self._session, user_id=actor.id, action="GROUP_DELETED",
            category="academic", entity_type="group", entity_id=group_id,
            metadata={"name": group.name}, ip_address=ip,
        )
        await self._repo.delete(group)
