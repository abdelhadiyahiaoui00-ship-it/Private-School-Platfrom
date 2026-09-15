from fastapi import APIRouter, Query, HTTPException
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


@router.get("/my", summary="Get current user's own activity log")
async def get_my_logs(
    actor: CurrentUser,
    session: DBSessionDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, alias="pageSize", ge=1, le=1000),
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


# ─── Admin: All Logs (Sprint 11) ──────────────────────────────────────────────

@router.get("", summary="List all activity logs (owner/superAdmin/admin with viewLogs)")
async def list_all_logs(
    actor: CurrentUser,
    session: DBSessionDep,
    branch_id: Optional[int] = Query(None, alias="branchId"),
    user_id: Optional[int] = Query(None, alias="userId"),
    category: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, alias="pageSize", ge=1, le=200),
):
    from sqlalchemy import func

    # Authorization
    is_privileged = actor.role in ("owner", "superAdmin")
    is_scoped_admin = (
        actor.role == "admin"
        and (actor.permissions or {}).get("viewLogs", False)
    )
    if not is_privileged and not is_scoped_admin:
        raise HTTPException(status_code=403, detail="Forbidden")

    q = select(ActivityLog)

    # Admin scoped to their branches
    if is_scoped_admin and not is_privileged:
        admin_branch_ids = [b.branch_id for b in getattr(actor, "branch_links", [])]
        if admin_branch_ids:
            q = q.where(ActivityLog.branch_id.in_(admin_branch_ids))

    # Filters
    if branch_id:
        q = q.where(ActivityLog.branch_id == branch_id)
    if user_id:
        q = q.where(ActivityLog.user_id == user_id)
    if category:
        q = q.where(ActivityLog.category == category)
    if action:
        q = q.where(ActivityLog.action.ilike(f"%{action}%"))

    q = q.order_by(ActivityLog.created_at.desc())

    # Total count
    count_q = select(func.count()).select_from(q.subquery())
    total = (await session.execute(count_q)).scalar_one()

    # Paginate
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
