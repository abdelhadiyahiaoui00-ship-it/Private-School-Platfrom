from typing import Optional
from fastapi import APIRouter, Depends, Query, Request

from src.core.database import DBSessionDep
from src.modules.auth.dependencies import require_manage_subscriptions
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
    page_size: int = Query(20, alias="pageSize", ge=1, le=1000),
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


# IMPORTANT: /stats would conflict with /{sub_id} — removed entirely (not in spec)
# Stats are inside GET /subscriptions response as "stats" field


@router.get("/{subscription_id}", summary="Get subscription detail")
async def get_subscription(
    subscription_id: int,
    actor: User = Depends(require_manage_subscriptions),
    service: SubscriptionService = Depends(get_service),
):
    result = await service.get_subscription(subscription_id, actor)
    return {"data": result}


@router.post("/{subscription_id}/renew", status_code=201, summary="Renew subscription")
async def renew_subscription(
    subscription_id: int,
    body: RenewSubscriptionRequest,
    request: Request,
    actor: User = Depends(require_manage_subscriptions),
    service: SubscriptionService = Depends(get_service),
):
    ip = request.client.host if request.client else None
    result = await service.renew_subscription(
        subscription_id, body.model_dump(by_alias=False), actor, ip=ip
    )
    return {"data": result}


@router.post("/{subscription_id}/extend", summary="Extend subscription (free compensation)")
async def extend_subscription(
    subscription_id: int,
    body: ExtendSubscriptionRequest,
    request: Request,
    actor: User = Depends(require_manage_subscriptions),
    service: SubscriptionService = Depends(get_service),
):
    ip = request.client.host if request.client else None
    result = await service.extend_subscription(
        subscription_id, body.model_dump(by_alias=False), actor, ip=ip
    )
    return {"data": result.model_dump(by_alias=True) if hasattr(result, "model_dump") else result}


@router.delete("/{subscription_id}", summary="Cancel subscription")
async def cancel_subscription(
    subscription_id: int,
    body: CancelSubscriptionRequest,
    request: Request,
    actor: User = Depends(require_manage_subscriptions),
    service: SubscriptionService = Depends(get_service),
):
    ip = request.client.host if request.client else None
    result = await service.cancel_subscription(
        subscription_id, actor, body.reason, ip=ip
    )
    return {"data": result}
