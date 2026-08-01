from typing import Optional
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.modules.auth.dependencies import get_current_user, require_manage_enrollments
from src.modules.enrollments.service import EnrollmentService
from src.modules.users.models import User
import slowapi

# Visitor Rate Limiting
from src.core.limiter import limiter

visitor_router = APIRouter(prefix="/visitor-reservations", tags=["Visitor Reservations"])
enrollment_router = APIRouter(prefix="/enrollments", tags=["Enrollments"])


def get_enrollment_service(db: AsyncSession = Depends(get_db)) -> EnrollmentService:
    return EnrollmentService(db)


# ─── VISITOR RESERVATIONS (Public) ────────────────────────────────────────

@visitor_router.post(
    "",
    summary="Create a visitor enrollment reservation",
    status_code=201
)
@limiter.limit("5/minute")
async def create_visitor_reservation(
    request: Request,
    data: dict,
    service: EnrollmentService = Depends(get_enrollment_service),
):
    ip = request.client.host if request.client else None
    result = await service.create_visitor_reservation(data, ip=ip)
    return {"data": result}


# ─── ENROLLMENTS (Authenticated / Admin) ──────────────────────────────────

@enrollment_router.get("/my", summary="Get my enrollments")
async def get_my_enrollments(
    actor: User = Depends(get_current_user),
    service: EnrollmentService = Depends(get_enrollment_service),
    child_id: Optional[int] = Query(None, alias="childId"),
    status: Optional[str] = Query(None),
):
    result = await service.get_my_enrollments(actor, child_id, status)
    return {"data": result}


@enrollment_router.get("/my-children", summary="Get linked children (Parent)")
async def get_my_children(
    actor: User = Depends(get_current_user),
    service: EnrollmentService = Depends(get_enrollment_service),
):
    result = await service.get_my_children(actor)
    return {"data": result}


@enrollment_router.get("/visitors", summary="List visitor enrollment requests")
async def list_visitor_requests(
    actor: User = Depends(require_manage_enrollments),
    service: EnrollmentService = Depends(get_enrollment_service),
    status: str = Query("pending"),
    branch_id: Optional[int] = Query(None, alias="branchId"),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=100),
):
    result = await service.list_visitor_requests({
        "status": status,
        "branch_id": branch_id,
        "search": search,
        "page": page,
        "page_size": page_size,
    }, actor)
    return {"data": result}


@enrollment_router.post("/visitors/{request_id}/convert", summary="Convert visitor request to student")
async def convert_visitor(
    request: Request,
    request_id: int,
    data: dict,
    actor: User = Depends(require_manage_enrollments),
    service: EnrollmentService = Depends(get_enrollment_service),
):
    ip = request.client.host if request.client else None
    result = await service.convert_visitor(request_id, data, actor, ip=ip)
    return {"data": result}


@enrollment_router.post("/visitors/{request_id}/reject", summary="Reject visitor request")
async def reject_visitor(
    request: Request,
    request_id: int,
    data: dict,
    actor: User = Depends(require_manage_enrollments),
    service: EnrollmentService = Depends(get_enrollment_service),
):
    ip = request.client.host if request.client else None
    await service.reject_visitor(request_id, actor, data.get("reason"), ip=ip)
    return {"data": {"success": True}}


@enrollment_router.get("", summary="List enrollments (Admin)")
async def list_enrollments(
    actor: User = Depends(require_manage_enrollments),
    service: EnrollmentService = Depends(get_enrollment_service),
    search: Optional[str] = Query(None),
    branch_id: Optional[int] = Query(None, alias="branchId"),
    group_id: Optional[int] = Query(None, alias="groupId"),
    class_id: Optional[int] = Query(None, alias="classId"),
    status: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    overdue_only: bool = Query(False, alias="overdueOnly"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=100),
    sort_by: str = Query("created_at", alias="sortBy"),
    sort_order: str = Query("desc", alias="sortOrder"),
):
    result = await service.list_enrollments({
        "search": search,
        "branch_id": branch_id,
        "group_id": group_id,
        "class_id": class_id,
        "status": status,
        "source": source,
        "overdue_only": overdue_only,
        "page": page,
        "page_size": page_size,
        "sort_by": sort_by,
        "sort_order": sort_order,
    }, actor)
    return {"data": result}


@enrollment_router.post("", summary="Create enrollment (Authenticated)")
async def create_enrollment(
    request: Request,
    data: dict,
    actor: User = Depends(get_current_user),
    service: EnrollmentService = Depends(get_enrollment_service),
):
    ip = request.client.host if request.client else None
    result = await service.create_enrollment(data, actor, ip=ip)
    return {"data": result.model_dump(by_alias=True)}


@enrollment_router.get("/{enrollment_id}", summary="Get enrollment details")
async def get_enrollment(
    enrollment_id: int,
    actor: User = Depends(get_current_user),
    service: EnrollmentService = Depends(get_enrollment_service),
):
    # Authorization logic is mostly inside service methods where needed,
    # or the repo filters based on the actor. Admin can see any.
    result = await service.get_enrollment(enrollment_id, actor)
    return {"data": result}


@enrollment_router.post("/{enrollment_id}/cancel", summary="Cancel enrollment")
async def cancel_enrollment(
    request: Request,
    enrollment_id: int,
    data: dict,
    actor: User = Depends(get_current_user),
    service: EnrollmentService = Depends(get_enrollment_service),
):
    ip = request.client.host if request.client else None
    result = await service.cancel_enrollment(enrollment_id, actor, data.get("reason"), ip=ip)
    return {"data": result}


@enrollment_router.post("/{enrollment_id}/promote", summary="Manually promote waitlisted enrollment")
async def promote_enrollment(
    request: Request,
    enrollment_id: int,
    actor: User = Depends(require_manage_enrollments),
    service: EnrollmentService = Depends(get_enrollment_service),
):
    ip = request.client.host if request.client else None
    result = await service.promote_enrollment(enrollment_id, actor, ip=ip)
    return {"data": result.model_dump(by_alias=True)}
