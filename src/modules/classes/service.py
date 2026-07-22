from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.level_rank import compute_level_rank, validate_level_targeting
from src.common.pagination import build_pagination
from src.modules.audit.service import log_action
from src.modules.classes.exceptions import (
    ClassHasActiveDependencies, ClassNotFound,
    InvalidLevelTargeting, TeacherNotAssignedToBranch
)
from src.modules.classes.models import Class
from src.modules.classes.repository import ClassRepository
from src.modules.classes.schemas import (
    ClassDetailResponse, ClassResponse, GroupSummary,
    LevelTargetingSchema, TeacherBasic
)
from src.modules.users.models import User


def _format_schedule_summary(schedule: list) -> str:
    if not schedule:
        return ""
    day_names = {0: "أحد", 1: "اثن", 2: "ثلث", 3: "أرب", 4: "خمس", 5: "جمع", 6: "سبت"}
    parts = []
    for slot in schedule:
        day = day_names.get(slot.get("dayOfWeek", 0), "")
        start = slot.get("startTime", "")[:5]
        end = slot.get("endTime", "")[:5]
        parts.append(f"{day} {start}–{end}")
    return "، ".join(parts)


def _build_level(cls: Class) -> LevelTargetingSchema:
    return LevelTargetingSchema(
        education_stage=cls.education_stage,
        education_year=cls.education_year,
        level_scope=cls.level_scope,
        min_age=cls.min_age,
        max_age=cls.max_age,
        university_label=cls.university_label,
        level_rank=cls.level_rank,
    )


def _build_teacher(user) -> TeacherBasic:
    return TeacherBasic(
        id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        avatar_url=user.avatar_url,
        default_commission_percent=float(user.default_commission_percent)
        if user.default_commission_percent is not None else None,
    )


def _build_response(cls: Class, groups_count: int = 0) -> ClassResponse:
    effective_commission = (
        float(cls.commission_percent) if cls.commission_percent is not None
        else (
            float(cls.teacher.default_commission_percent)
            if cls.teacher and cls.teacher.default_commission_percent is not None
            else 0.0
        )
    )
    return ClassResponse(
        id=cls.id,
        branch_id=cls.branch_id,
        branch_name=cls.branch.name if cls.branch else "",
        module_id=cls.module_id,
        module_name=cls.module.name if cls.module else "",
        module_color=cls.module.color if cls.module else None,
        teacher=_build_teacher(cls.teacher),
        name=cls.name,
        period_start=cls.period_start,
        period_end=cls.period_end,
        commission_percent=float(cls.commission_percent) if cls.commission_percent else None,
        effective_commission_percent=effective_commission,
        level=_build_level(cls),
        status=cls.status,
        groups_count=groups_count,
        created_by=cls.created_by,
        created_at=cls.created_at,
        updated_at=cls.updated_at,
    )


class ClassService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ClassRepository(session)

    def _get_branch_scope(self, actor: User) -> Optional[list[int]]:
        if actor.role == "admin":
            return [ub.branch_id for ub in (actor.branch_links or [])]
        return None

    async def list_classes(self, params: dict, actor: User) -> dict:
        branch_ids_scope = self._get_branch_scope(actor)
        classes, total = await self._repo.get_all(
            search=params.get("search"),
            branch_id=params.get("branch_id"),
            module_id=params.get("module_id"),
            teacher_id=params.get("teacher_id"),
            status=params.get("status", "active"),
            education_stage=params.get("education_stage"),
            page=params.get("page", 1),
            page_size=params.get("page_size", 20),
            sort_by=params.get("sort_by", "created_at"),
            sort_order=params.get("sort_order", "desc"),
            branch_ids_scope=branch_ids_scope,
        )
        stats = await self._repo.get_stats(branch_ids_scope)
        items = []
        for cls in classes:
            cnt = await self._repo.get_groups_count(cls.id)
            items.append(_build_response(cls, cnt).model_dump(by_alias=True))
        return {
            "items": items,
            "pagination": build_pagination(params.get("page", 1), params.get("page_size", 20), total),
            "stats": stats,
        }

    async def get_class(self, class_id: int, actor: User) -> dict:
        cls = await self._repo.get_by_id(class_id)
        if not cls:
            raise ClassNotFound()
        branch_ids_scope = self._get_branch_scope(actor)
        if branch_ids_scope is not None and cls.branch_id not in branch_ids_scope:
            from src.core.exceptions import ForbiddenBranch
            raise ForbiddenBranch()

        groups_summary_rows = await self._repo.get_groups_summary(class_id)
        groups_summary = [
            GroupSummary(
                id=g.id,
                name=g.name,
                schedule_summary=_format_schedule_summary(g.schedule),
                max_students=g.max_students,
            )
            for g in groups_summary_rows
        ]
        cnt = len(groups_summary_rows)
        base = _build_response(cls, cnt)
        detail = ClassDetailResponse(**base.model_dump(), groups_summary=groups_summary)
        return detail.model_dump(by_alias=True)

    async def _validate_and_set_level(self, data: dict, cls: Class) -> None:
        level_scope = data.get("level_scope", cls.level_scope)
        education_stage = data.get("education_stage", cls.education_stage)
        education_year = data.get("education_year", cls.education_year)
        min_age = data.get("min_age", cls.min_age)
        max_age = data.get("max_age", cls.max_age)

        errors = validate_level_targeting(level_scope, education_stage, education_year, min_age, max_age)
        if errors:
            raise InvalidLevelTargeting(
                message="Level targeting fields are inconsistent.",
                details=errors,
            )

        cls.level_scope = level_scope
        cls.education_stage = education_stage
        cls.education_year = education_year
        cls.min_age = min_age
        cls.max_age = max_age
        cls.university_label = data.get("university_label", cls.university_label)
        cls.level_rank = compute_level_rank(level_scope, education_stage, education_year)

    async def create_class(self, data: dict, actor: User, ip: Optional[str] = None) -> dict:
        branch_id = data["branch_id"]
        branch_ids_scope = self._get_branch_scope(actor)
        if branch_ids_scope is not None and branch_id not in branch_ids_scope:
            from src.core.exceptions import ForbiddenBranch
            raise ForbiddenBranch()

        teacher_id = data["teacher_id"]
        if actor.role == "admin":
            if not await self._repo.teacher_assigned_to_branch(teacher_id, branch_id):
                raise TeacherNotAssignedToBranch()

        level_scope = data.get("level_scope", "all_levels")
        education_stage = data.get("education_stage", "all")
        education_year = data.get("education_year")
        min_age = data.get("min_age")
        max_age = data.get("max_age")

        errors = validate_level_targeting(level_scope, education_stage, education_year, min_age, max_age)
        if errors:
            raise InvalidLevelTargeting(message="Level targeting fields are inconsistent.", details=errors)

        level_rank = compute_level_rank(level_scope, education_stage, education_year)

        cls = Class(
            branch_id=branch_id,
            module_id=data["module_id"],
            teacher_id=teacher_id,
            name=data["name"],
            period_start=data.get("period_start"),
            period_end=data.get("period_end"),
            commission_percent=data.get("commission_percent"),
            education_stage=education_stage,
            education_year=education_year,
            level_scope=level_scope,
            min_age=min_age,
            max_age=max_age,
            university_label=data.get("university_label"),
            level_rank=level_rank,
            status="active",
            created_by=actor.id,
        )
        cls = await self._repo.create(cls)
        await log_action(
            self._session, user_id=actor.id, action="CLASS_CREATED",
            category="academic", entity_type="class", entity_id=cls.id,
            metadata={"moduleId": data["module_id"], "teacherId": teacher_id, "branchId": branch_id},
            ip_address=ip,
        )
        cls = await self._repo.get_by_id(cls.id)
        return _build_response(cls, 0).model_dump(by_alias=True)

    async def update_class(self, class_id: int, data: dict, actor: User, ip: Optional[str] = None) -> dict:
        cls = await self._repo.get_by_id(class_id)
        if not cls:
            raise ClassNotFound()
        branch_ids_scope = self._get_branch_scope(actor)
        if branch_ids_scope is not None and cls.branch_id not in branch_ids_scope:
            from src.core.exceptions import ForbiddenBranch
            raise ForbiddenBranch()

        changed = []
        for field in ("module_id", "teacher_id", "name", "period_start", "period_end", "commission_percent"):
            if field in data:
                setattr(cls, field, data[field])
                changed.append(field)

        level_fields = {"level_scope", "education_stage", "education_year", "min_age", "max_age", "university_label"}
        if any(f in data for f in level_fields):
            await self._validate_and_set_level(data, cls)
            changed.append("level")

        cls = await self._repo.save(cls)
        await log_action(
            self._session, user_id=actor.id, action="CLASS_UPDATED",
            category="academic", entity_type="class", entity_id=class_id,
            metadata={"changedFields": changed}, ip_address=ip,
        )
        cls = await self._repo.get_by_id(class_id)
        cnt = await self._repo.get_groups_count(class_id)
        return _build_response(cls, cnt).model_dump(by_alias=True)

    async def set_status(self, class_id: int, status: str, cascade_groups: bool, actor: User, ip: Optional[str] = None) -> dict:
        cls = await self._repo.get_by_id(class_id)
        if not cls:
            raise ClassNotFound()
        cls.status = status
        if status == "archived" and cascade_groups:
            groups = await self._repo.get_groups_summary(class_id)
            for g in groups:
                g.status = "archived"
        await self._repo.save(cls)
        await log_action(
            self._session, user_id=actor.id, action="CLASS_UPDATED",
            category="academic", entity_type="class", entity_id=class_id,
            metadata={"changedFields": ["status"], "status": status, "cascadeGroups": cascade_groups},
            ip_address=ip,
        )
        cnt = await self._repo.get_groups_count(class_id)
        return _build_response(cls, cnt).model_dump(by_alias=True)

    async def delete_class(self, class_id: int, actor: User, ip: Optional[str] = None) -> None:
        cls = await self._repo.get_by_id(class_id)
        if not cls:
            raise ClassNotFound()
        if await self._repo.has_any_sessions(class_id):
            raise ClassHasActiveDependencies()
        await log_action(
            self._session, user_id=actor.id, action="CLASS_DELETED",
            category="academic", entity_type="class", entity_id=class_id,
            metadata={"name": cls.name}, ip_address=ip,
        )
        await self._repo.delete(cls)
