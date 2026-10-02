from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from datetime import datetime, date, timedelta, timezone

from sqlalchemy import select, func, cast, String, or_
from sqlalchemy.orm import aliased

from src.core.database import DBSessionDep
from src.modules.auth.dependencies import CurrentUser
from src.modules.audit.models import ActivityLog
from src.modules.users.models import User
from src.common.pagination import build_pagination
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

router = APIRouter(prefix="/logs", tags=["Logs"])

# ─── Allowed log categories (fixed set) ───────────────────────────────────────
_ALL_CATEGORIES = (
    "auth",
    "users",
    "branches",
    "academic",
    "enrollments",
    "subscriptions",
    "sessions",
    "assignments",
    "system",
)

# ─── Response schema ──────────────────────────────────────────────────────────

class ActivityLogResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)

    id: int
    user_id: Optional[int] = None
    actor_name: Optional[str] = None
    actor_role: Optional[str] = None
    action: str
    category: str
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    branch_id: Optional[int] = None
    metadata: Optional[dict] = Field(None, validation_alias="metadata_")
    ip_address: Optional[str] = None
    created_at: datetime


# ─── GET /logs/my ─────────────────────────────────────────────────────────────

@router.get("/my", summary="Get current user's own activity log")
async def get_my_logs(
    actor: CurrentUser,
    session: DBSessionDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, alias="pageSize", ge=1, le=1000),
    category: Optional[str] = Query(None),
):
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


# ─── Admin: All Logs ──────────────────────────────────────────────────────────

@router.get("", summary="List all activity logs (owner/superAdmin/admin with viewLogs)")
async def list_all_logs(
    actor: CurrentUser,
    session: DBSessionDep,
    branch_id: Optional[int] = Query(None, alias="branchId"),
    actor_id: Optional[int] = Query(None, alias="actorId"),
    category: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None, alias="dateFrom"),
    date_to: Optional[date] = Query(None, alias="dateTo"),
    search: Optional[str] = Query(None),
    sort_order: str = Query("desc", alias="sortOrder", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, alias="pageSize", ge=1, le=1000),
):
    # ── Authorization ─────────────────────────────────────────────────────────
    is_privileged = actor.role in ("owner", "superAdmin")
    is_scoped_admin = (
        actor.role == "admin"
        and (actor.permissions or {}).get("viewLogs", False)
    )
    if not is_privileged and not is_scoped_admin:
        raise HTTPException(status_code=403, detail="Forbidden")

    # ── Join User for actor name/role ─────────────────────────────────────────
    ActorUser = aliased(User, flat=True)

    # ── Build base filter (applied to both list and categoryCounts) ───────────
    def _apply_base_filters(q, *, include_category: bool = True):
        """Apply all filters except pagination/ordering. category excluded for
        category counts query."""
        # Scope admin to their assigned branches
        if is_scoped_admin and not is_privileged:
            admin_branch_ids = [b.branch_id for b in getattr(actor, "branch_links", [])]
            if admin_branch_ids:
                q = q.where(ActivityLog.branch_id.in_(admin_branch_ids))

        if branch_id:
            q = q.where(ActivityLog.branch_id == branch_id)
        if actor_id:
            q = q.where(ActivityLog.user_id == actor_id)
        if include_category and category:
            q = q.where(ActivityLog.category == category)
        if date_from:
            start_dt = datetime(date_from.year, date_from.month, date_from.day, tzinfo=timezone.utc)
            q = q.where(ActivityLog.created_at >= start_dt)
        if date_to:
            # inclusive through 23:59:59 on dateTo
            end_dt = datetime(date_to.year, date_to.month, date_to.day, tzinfo=timezone.utc) + timedelta(days=1)
            q = q.where(ActivityLog.created_at < end_dt)
        if search:
            like_pat = f"%{search}%"
            q = q.where(
                or_(
                    (func.concat(ActorUser.first_name, " ", ActorUser.last_name).ilike(like_pat)),
                    cast(ActivityLog.metadata_, String).ilike(like_pat),
                )
            )
        return q

    # ── Category counts (GROUP BY, no category filter, no pagination) ─────────
    counts_base = (
        select(ActivityLog.category, func.count().label("cnt"))
        .join(ActorUser, ActivityLog.user_id == ActorUser.id, isouter=True)
    )
    counts_base = _apply_base_filters(counts_base, include_category=False)
    counts_base = counts_base.group_by(ActivityLog.category)
    counts_result = await session.execute(counts_base)
    raw_counts = {row.category: row.cnt for row in counts_result.all()}

    category_counts = {cat: raw_counts.get(cat, 0) for cat in _ALL_CATEGORIES}

    # ── Main list query ───────────────────────────────────────────────────────
    list_q = (
        select(ActivityLog, ActorUser)
        .join(ActorUser, ActivityLog.user_id == ActorUser.id, isouter=True)
    )
    list_q = _apply_base_filters(list_q, include_category=True)

    # Total count (without pagination)
    count_q = select(func.count()).select_from(list_q.subquery())
    total = (await session.execute(count_q)).scalar_one()

    # Ordering
    if sort_order == "asc":
        list_q = list_q.order_by(ActivityLog.created_at.asc())
    else:
        list_q = list_q.order_by(ActivityLog.created_at.desc())

    # Paginate
    list_q = list_q.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(list_q)
    rows = result.all()

    # ── Serialize ─────────────────────────────────────────────────────────────
    def _serialize_log(log: ActivityLog, user: Optional[User]) -> dict:
        actor_name: Optional[str] = None
        actor_role: Optional[str] = None
        if user is not None and log.user_id is not None:
            full_name = f"{user.first_name} {user.last_name}".strip()
            actor_name = full_name if full_name else None
            actor_role = user.role or None

        return {
            "id": log.id,
            "userId": log.user_id,
            "actorName": actor_name,
            "actorRole": actor_role,
            "action": log.action,
            "category": log.category,
            "entityType": log.entity_type,
            "entityId": log.entity_id,
            "branchId": log.branch_id,
            "metadata": log.metadata_,
            "ipAddress": log.ip_address,
            "createdAt": log.created_at.isoformat() if log.created_at else None,
        }

    items = [_serialize_log(log, user) for log, user in rows]

    pagination = build_pagination(page, page_size, total)
    return {
        "data": {
            "items": items,
            "pagination": pagination,
            "categoryCounts": category_counts,
        }
    }
