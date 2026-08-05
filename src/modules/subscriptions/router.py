from typing import Optional
from fastapi import APIRouter, Depends, Query, Request

from src.core.database import DBSessionDep
from src.modules.auth.dependencies import CurrentUser, require_role
from src.modules.users.models import User
from src.modules.subscriptions.schemas import (
    RenewSubscriptionRequest,
    ExtendSubscriptionRequest,
    CancelSubscriptionRequest,
)
from src.modules.subscriptions.service import SubscriptionService

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])

def get_service(session: DBSessionDep) -> SubscriptionService:
    return SubscriptionService(session)

def require_manage_subscriptions(user: User = Depends(require_role(["owner", "superAdmin", "admin"]))) -> User:
    if user.role in ("owner", "superAdmin"):
        return user
    if user.role == "admin":
        perms = user.permissions or {}
        if perms.get("manageSubscriptions"):
            return user
    from src.core.exceptions import PermissionDenied
    raise PermissionDenied(message="Requires manageSubscriptions permission.")

@router.get("", summary="List subscriptions")
async def list_subscriptions(
    actor: User = Depends(require_manage_subscriptions),
    service: SubscriptionService = Depends(get_service),
    search: Optional[str] = Query(None),
    branch_id: Optional[int] = Query(None, alias="branchId"),
    group_id: Optional[int] = Query(None, alias="groupId"),
    class_id: Optional[int] = Query(None, alias="classId"),
    module_id: Optional[int] = Query(None, alias="moduleId"),
    teacher_id: Optional[int] = Query(None, alias="teacherId"),
    type: Optional[str] = Query(None),
    status: str = Query("active"),
    expiring_soon_only: bool = Query(False, alias="expiringSoonOnly"),
    expired_only: bool = Query(False, alias="expiredOnly"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=100),
    sort_by: str = Query("createdAt", alias="sortBy"),
    sort_order: str = Query("desc", alias="sortOrder"),
):
    result = await service.list_subscriptions({
        "search": search, "branch_id": branch_id, "group_id": group_id,
        "class_id": class_id, "module_id": module_id, "teacher_id": teacher_id,
        "type": type, "status": status,
        "expiring_soon_only": expiring_soon_only, "expired_only": expired_only,
        "page": page, "page_size": page_size,
        "sort_by": sort_by, "sort_order": sort_order,
    }, actor)
    return {"data": result}

@router.get("/stats", summary="Get subscriptions stats")
async def get_stats(
    actor: User = Depends(require_manage_subscriptions),
    service: SubscriptionService = Depends(get_service),
):
    result = await service.get_stats(actor)
    return {"data": result}

@router.get("/{sub_id}", summary="Get subscription detail")
async def get_subscription(
    sub_id: int,
    actor: User = Depends(require_manage_subscriptions),
    service: SubscriptionService = Depends(get_service),
):
    result = await service.get_subscription(sub_id, actor)
    return {"data": result}

@router.post("/{sub_id}/renew", summary="Renew subscription")
async def renew_subscription(
    sub_id: int,
    body: RenewSubscriptionRequest,
    request: Request,
    actor: User = Depends(require_manage_subscriptions),
    service: SubscriptionService = Depends(get_service),
):
    ip = request.client.host if request.client else None
    result = await service.renew_subscription(sub_id, body.model_dump(exclude_none=True), actor, ip=ip)
    return {"data": result}

@router.post("/{sub_id}/extend", summary="Extend subscription")
async def extend_subscription(
    sub_id: int,
    body: ExtendSubscriptionRequest,
    request: Request,
    actor: User = Depends(require_manage_subscriptions),
    service: SubscriptionService = Depends(get_service),
):
    ip = request.client.host if request.client else None
    result = await service.extend_subscription(sub_id, body.model_dump(exclude_none=True), actor, ip=ip)
    return {"data": result}

@router.delete("/{sub_id}", summary="Cancel subscription")
async def cancel_subscription(
    sub_id: int,
    body: CancelSubscriptionRequest,
    request: Request,
    actor: User = Depends(require_manage_subscriptions),
    service: SubscriptionService = Depends(get_service),
):
    ip = request.client.host if request.client else None
    result = await service.cancel_subscription(sub_id, body.model_dump(exclude_none=True), actor, ip=ip)
    return {"data": result}
