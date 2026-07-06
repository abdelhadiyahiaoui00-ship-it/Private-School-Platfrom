import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request, Response

from src.core.config import settings
from src.core.database import DBSessionDep
from src.modules.public.service import PublicService
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(settings.APP_NAME)

router = APIRouter(prefix="/public", tags=["Public"])
limiter = Limiter(key_func=get_remote_address)


def get_public_service(session: DBSessionDep) -> PublicService:
    return PublicService(session)


# ─── GET /public/catalog ──────────────────────────────────────────────────────

@router.get("/catalog", summary="Public class catalog")
@limiter.limit("60/minute")
async def get_catalog(
    request: Request,
    response: Response,
    session: DBSessionDep,
    search: Optional[str] = Query(None),
    branch_id: Optional[int] = Query(None, alias="branchId"),
    module_id: Optional[int] = Query(None, alias="moduleId"),
    day_of_week: Optional[int] = Query(None, alias="dayOfWeek", ge=0, le=6),
    subscription_type: Optional[str] = Query(None, alias="subscriptionType"),
    featured: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(12, alias="pageSize", ge=1, le=48),
):
    """No auth required. Returns active groups from active classes in active branches."""
    response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=600"

    service = PublicService(session)
    data = await service.get_catalog(
        search=search or None,
        branch_id=branch_id,
        module_id=module_id,
        day_of_week=day_of_week,
        subscription_type=subscription_type,
        featured=featured,
        page=page,
        page_size=page_size,
    )
    return {"data": data}


# ─── GET /public/catalog/:groupId ─────────────────────────────────────────────
# Defined AFTER /catalog so FastAPI doesn't treat "catalog" as an integer groupId

@router.get("/catalog/{group_id}", summary="Public group detail")
async def get_group_detail(
    group_id: int,
    response: Response,
    session: DBSessionDep,
):
    """No auth required. Returns full group detail including sessions preview."""
    response.headers["Cache-Control"] = "public, max-age=300"

    service = PublicService(session)
    data = await service.get_group_detail(group_id)

    if data is None:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Group not found."}},
        )

    return {"data": data}


# ─── GET /public/branches ─────────────────────────────────────────────────────

@router.get("/branches", summary="Public branches list")
async def get_public_branches(
    response: Response,
    session: DBSessionDep,
):
    """No auth required. Returns all active branches with location and photo data."""
    response.headers["Cache-Control"] = "public, max-age=600"

    service = PublicService(session)
    items = await service.get_public_branches()
    return {"data": {"items": items}}
