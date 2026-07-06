import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.common.pagination import build_pagination
from src.core.config import settings
from src.modules.groups.models import Group
from src.modules.public.repository import PublicRepository
from src.modules.public.schemas import (
    PublicBranchResponse,
    PublicGroupDetailResponse,
    PublicGroupResponse,
    PublicTeacherBasic,
)

logger = logging.getLogger(settings.APP_NAME)


def _build_teacher(user) -> PublicTeacherBasic:
    if not user:
        return PublicTeacherBasic(id=0, first_name="", last_name="", avatar_url=None)
    return PublicTeacherBasic(
        id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        avatar_url=user.avatar_url,
    )


def _build_group_response(group: Group, active_enrollments: int) -> PublicGroupResponse:
    cls = group.class_
    # effective teacher: group override OR class teacher
    teacher_obj = group.teacher or (cls.teacher if cls else None)
    available_seats = max(0, group.max_students - active_enrollments)

    return PublicGroupResponse(
        id=group.id,
        name=group.name,
        class_id=cls.id if cls else 0,
        class_name=cls.name if cls else "",
        module_id=cls.module_id if cls else 0,
        module_name=cls.module.name if cls and cls.module else "",
        module_category=cls.module.category if cls and cls.module else None,
        teacher=_build_teacher(teacher_obj),
        branch_id=cls.branch_id if cls else 0,
        branch_name=cls.branch.name if cls and cls.branch else "",
        schedule=group.schedule or [],
        room=group.room,
        price=float(group.price),
        subscription_type=group.subscription_type,
        session_count=group.session_count,
        max_students=group.max_students,
        active_enrollments=active_enrollments,
        is_full=active_enrollments >= group.max_students,
        available_seats=available_seats,
    )


class PublicService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = PublicRepository(session)

    async def get_catalog(
        self,
        search: Optional[str] = None,
        branch_id: Optional[int] = None,
        module_id: Optional[int] = None,
        day_of_week: Optional[int] = None,
        subscription_type: Optional[str] = None,
        featured: Optional[bool] = None,
        page: int = 1,
        page_size: int = 12,
    ) -> dict:
        try:
            if featured:
                groups = await self._repo.get_featured_groups(limit=6)
                group_ids = [g.id for g in groups]
                counts = await self._repo.get_enrollment_counts_bulk(group_ids)
                items = [_build_group_response(g, counts.get(g.id, 0)) for g in groups]
                filter_options = await self._repo.get_filter_options()
                return {
                    "items": [i.model_dump(by_alias=True) for i in items],
                    "pagination": build_pagination(1, 6, len(items)),
                    "filters": filter_options,
                }

            groups, total = await self._repo.get_active_groups(
                search=search,
                branch_id=branch_id,
                module_id=module_id,
                day_of_week=day_of_week,
                subscription_type=subscription_type,
                page=page,
                page_size=page_size,
            )
            group_ids = [g.id for g in groups]
            counts = await self._repo.get_enrollment_counts_bulk(group_ids)
            items = [_build_group_response(g, counts.get(g.id, 0)) for g in groups]
            filter_options = await self._repo.get_filter_options()

            return {
                "items": [i.model_dump(by_alias=True) for i in items],
                "pagination": build_pagination(page, page_size, total),
                "filters": filter_options,
            }
        except Exception as exc:
            logger.error(f"Public catalog error: {exc}", exc_info=True)
            return {
                "items": [],
                "pagination": build_pagination(page, page_size, 0),
                "filters": {"branches": [], "modules": []},
            }

    async def get_group_detail(self, group_id: int) -> Optional[dict]:
        try:
            group = await self._repo.get_group_by_id(group_id)
            if not group:
                return None

            active_enrollments = await self._repo.get_active_enrollment_count(group.id)
            base = _build_group_response(group, active_enrollments)

            cls = group.class_
            upcoming_sessions = await self._repo.get_upcoming_sessions(group.id, limit=3)
            sessions_preview = [
                {
                    "date": str(s.session_date),
                    "startTime": str(s.start_time)[:5],
                    "endTime": str(s.end_time)[:5],
                    "room": s.room,
                }
                for s in upcoming_sessions
            ]

            detail = PublicGroupDetailResponse(
                **base.model_dump(),
                class_description=cls.module.description if cls and cls.module else None,
                class_period_start=cls.period_start if cls else None,
                class_period_end=cls.period_end if cls else None,
                sessions_preview=sessions_preview,
            )
            return detail.model_dump(by_alias=True)
        except Exception as exc:
            logger.error(f"Public group detail error (id={group_id}): {exc}", exc_info=True)
            return None

    async def get_public_branches(self) -> list[dict]:
        try:
            branches = await self._repo.get_active_branches()
            result = []
            for b in branches:
                active_classes = await self._repo.get_active_classes_count(b.id)
                resp = PublicBranchResponse(
                    id=b.id,
                    name=b.name,
                    address=b.address,
                    phone=b.phone,
                    email=b.email,
                    latitude=float(b.latitude) if b.latitude is not None else None,
                    longitude=float(b.longitude) if b.longitude is not None else None,
                    map_embed_url=b.map_embed_url,
                    photo_urls=b.photo_urls or [],
                    description=b.description,
                    active_classes_count=active_classes,
                )
                result.append(resp.model_dump(by_alias=True))
            return result
        except Exception as exc:
            logger.error(f"Public branches error: {exc}", exc_info=True)
            return []
