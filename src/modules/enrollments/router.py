from typing import Optional
from fastapi import APIRouter, Depends, Query, Request

from src.core.database import DBSessionDep
from src.core.limiter import limiter
from src.modules.auth.dependencies import CurrentUser, require_manage_enrollments, get_current_user
from src.modules.enrollments.schemas import (
    CreateVisitorReservationRequest,
    ConvertVisitorRequest,
    RejectVisitorRequest,
    CreateEnrollmentRequest,
    CancelEnrollmentRequest,
    TransferGroupRequest,
)
from src.modules.subscriptions.schemas import ConfirmPaymentRequest
from src.modules.subscriptions.service import SubscriptionService
from src.modules.enrollments.service import EnrollmentService
from src.modules.users.models import User

# ─── Three separate routers ───────────────────────────────────────────────────
visitor_router = APIRouter(prefix="/visitor-enrollments", tags=["Visitor Enrollments"])
router = APIRouter(prefix="/enrollments", tags=["Enrollments"])
parent_links_router = APIRouter(prefix="/parent-links", tags=["Parent Links"])


def get_service(session: DBSessionDep) -> EnrollmentService:
    return EnrollmentService(session)


# ─── VISITOR RESERVATIONS (Public) ────────────────────────────────────────────

@visitor_router.post("", status_code=201, summary="Create visitor reservation (public)")
@limiter.limit("10/minute")
async def create_visitor_reservation(
    request: Request,
    body: CreateVisitorReservationRequest,
    service: EnrollmentService = Depends(get_service),
):
    ip = request.client.host if request.client else None
    result = await service.create_visitor_reservation(body.model_dump(by_alias=False), ip=ip)
    return {"data": result}


@visitor_router.get("", summary="List visitor enrollment requests (admin)")
async def list_visitor_requests(
    actor: User = Depends(require_manage_enrollments),
    service: EnrollmentService = Depends(get_service),
    status: str = Query("pending"),
    branch_id: Optional[int] = Query(None, alias="branchId"),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=1000),
):
    result = await service.list_visitor_requests({
        "status": status, "branch_id": branch_id,
        "search": search, "page": page, "page_size": page_size,
    }, actor)
    return {"data": result}


@visitor_router.post("/{request_id}/convert", summary="Convert visitor to real account")
async def convert_visitor(
    request_id: int,
    body: ConvertVisitorRequest,
    request: Request,
    actor: User = Depends(require_manage_enrollments),
    service: EnrollmentService = Depends(get_service),
):
    ip = request.client.host if request.client else None
    result = await service.convert_visitor(request_id, body.model_dump(by_alias=False), actor, ip=ip)
    return {"data": result}


@visitor_router.post("/{request_id}/reject", summary="Reject visitor request")
async def reject_visitor(
    request_id: int,
    body: RejectVisitorRequest,
    request: Request,
    actor: User = Depends(require_manage_enrollments),
    service: EnrollmentService = Depends(get_service),
):
    ip = request.client.host if request.client else None
    await service.reject_visitor(request_id, actor, body.reason, ip=ip)
    return {"data": {"rejected": True}}


# ─── ENROLLMENTS (Authenticated) ──────────────────────────────────────────────
# CRITICAL: /my must be defined BEFORE /{enrollment_id}

@router.get("/my", summary="Get my enrollments (student/parent)")
async def get_my_enrollments(
    actor: User = Depends(get_current_user),
    service: EnrollmentService = Depends(get_service),
    child_id: Optional[int] = Query(None, alias="childId"),
    status: Optional[str] = Query(None),
):
    items = await service.get_my_enrollments(actor, child_id=child_id, status=status)
    return {"data": {"items": items}}


@router.get("", summary="List enrollments (admin)")
async def list_enrollments(
    actor: User = Depends(require_manage_enrollments),
    service: EnrollmentService = Depends(get_service),
    search: Optional[str] = Query(None),
    branch_id: Optional[int] = Query(None, alias="branchId"),
    group_id: Optional[int] = Query(None, alias="groupId"),
    class_id: Optional[int] = Query(None, alias="classId"),
    status: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    overdue_only: bool = Query(False, alias="overdueOnly"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=1000),
    sort_by: str = Query("createdAt", alias="sortBy"),
    sort_order: str = Query("desc", alias="sortOrder"),
):
    result = await service.list_enrollments({
        "search": search, "branch_id": branch_id, "group_id": group_id,
        "class_id": class_id, "status": status, "source": source,
        "overdue_only": overdue_only, "page": page, "page_size": page_size,
        "sort_by": sort_by, "sort_order": sort_order,
    }, actor)
    return {"data": result}


# ─── Transfer Endpoints (Sprint 10) ──────────────────────────────────────────

@router.get("/{enrollment_id}/transfer-preview", summary="Preview group transfer")
async def transfer_preview(
    enrollment_id: int,
    target_group_id: int = Query(..., alias="targetGroupId"),
    actor: User = Depends(require_manage_enrollments),
    service: EnrollmentService = Depends(get_service),
):
    data = await service.transfer_preview(enrollment_id, target_group_id)
    return {"data": data}


@router.post("/{enrollment_id}/transfer-group", summary="Transfer to different group")
async def transfer_group(
    enrollment_id: int,
    body: TransferGroupRequest,
    request: Request,
    actor: User = Depends(require_manage_enrollments),
    service: EnrollmentService = Depends(get_service),
):
    ip = request.client.host if request.client else None
    is_admin = actor.role in ("owner", "superAdmin", "admin")
    data = await service.transfer_group(
        enrollment_id, body.target_group_id, actor.id, is_admin, actor_ip=ip
    )
    return {"data": data}



@router.get("/{enrollment_id}", summary="Get enrollment detail")
async def get_enrollment(
    enrollment_id: int,
    actor: User = Depends(require_manage_enrollments),
    service: EnrollmentService = Depends(get_service),
):
    result = await service.get_enrollment(enrollment_id, actor)
    return {"data": result}


@router.post("", status_code=201, summary="Enroll (authenticated)")
async def create_enrollment(
    body: CreateEnrollmentRequest,
    request: Request,
    actor: User = Depends(get_current_user),
    service: EnrollmentService = Depends(get_service),
):
    ip = request.client.host if request.client else None
    result = await service.create_enrollment(body.model_dump(by_alias=False), actor, ip=ip)
    return {"data": result.model_dump(by_alias=True) if hasattr(result, "model_dump") else result}


@router.delete("/{enrollment_id}", summary="Cancel enrollment")
async def cancel_enrollment(
    enrollment_id: int,
    body: CancelEnrollmentRequest,
    request: Request,
    actor: User = Depends(get_current_user),
    service: EnrollmentService = Depends(get_service),
):
    ip = request.client.host if request.client else None
    result = await service.cancel_enrollment(enrollment_id, actor, body.reason, ip=ip)
    return {"data": result}


@router.post("/{enrollment_id}/promote", summary="Manually promote from waitlist")
async def promote_enrollment(
    enrollment_id: int,
    request: Request,
    actor: User = Depends(require_manage_enrollments),
    service: EnrollmentService = Depends(get_service),
):
    ip = request.client.host if request.client else None
    result = await service.promote_enrollment(enrollment_id, actor, ip=ip)
    return {"data": result.model_dump(by_alias=True)}


@router.post("/{enrollment_id}/confirm-payment", summary="Confirm payment for pending enrollment")
async def confirm_payment(
    enrollment_id: int,
    body: ConfirmPaymentRequest,
    request: Request,
    session: DBSessionDep,
    actor: User = Depends(require_manage_enrollments),
):
    ip = request.client.host if request.client else None
    sub_service = SubscriptionService(session)
    result = await sub_service.confirm_payment_for_enrollment(
        enrollment_id, body.model_dump(exclude_none=True), actor, ip=ip
    )
    return {"data": result}


# ─── PARENT LINKS EXTENSION ───────────────────────────────────────────────────

@parent_links_router.get("/my-children", summary="Get parent's linked children")
async def get_my_children(
    actor: User = Depends(get_current_user),
    service: EnrollmentService = Depends(get_service),
):
    items = await service.get_my_children(actor)
    return {"data": {"items": items}}
