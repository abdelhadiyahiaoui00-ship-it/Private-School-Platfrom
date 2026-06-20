from fastapi import APIRouter, Query
from typing import Optional
from sqlalchemy import select
from src.core.database import DBSessionDep
from src.modules.auth.dependencies import CurrentUser
from src.modules.audit.models import ActivityLog
from src.common.pagination import build_pagination
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from datetime import datetime

router = APIRouter(prefix="/logs", tags=["Logs"])


class ActivityLogResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)

    id: int
    user_id: Optional[int] = None
    action: str
    category: str
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    metadata: Optional[dict] = None
    ip_address: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/my", summary="Get current user's own activity log")
async def get_my_logs(
    actor: CurrentUser,
    session: DBSessionDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, alias="pageSize", ge=1, le=100),
    category: Optional[str] = Query(None),
):
    from sqlalchemy import func
    q = select(ActivityLog).where(ActivityLog.user_id == actor.id)
    if category:
        q = q.where(ActivityLog.category == category)
    q = q.order_by(ActivityLog.created_at.desc())

    count_q = select(func.count()).select_from(
        select(ActivityLog).where(ActivityLog.user_id == actor.id).subquery()
    )
    total = (await session.execute(count_q)).scalar_one()

    q = q.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(q)
    items = list(result.scalars().all())

    pagination = build_pagination(page, page_size, total)
    return {
        "data": {
            "items": [ActivityLogResponse.model_validate(log).model_dump(by_alias=True) for log in items],
            "pagination": pagination,
        }
    }
