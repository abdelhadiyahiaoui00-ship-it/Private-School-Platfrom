from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query

from src.core.database import DBSessionDep
from src.modules.auth.dependencies import require_manage_subscriptions
from src.modules.payments.service import PaymentService
from src.modules.users.models import User

router = APIRouter(prefix="/payments", tags=["Payments"])


def get_service(session: DBSessionDep) -> PaymentService:
    return PaymentService(session)


@router.get("", summary="List payments / transactions ledger")
async def list_payments(
    actor: User = Depends(require_manage_subscriptions),
    service: PaymentService = Depends(get_service),
    search: Optional[str] = Query(None),
    branch_id: Optional[int] = Query(None, alias="branchId"),
    teacher_id: Optional[int] = Query(None, alias="teacherId"),
    module_id: Optional[int] = Query(None, alias="moduleId"),
    method: Optional[str] = Query(None),
    payment_type: Optional[str] = Query(None, alias="paymentType"),
    date_from: Optional[str] = Query(None, alias="dateFrom"),
    date_to: Optional[str] = Query(None, alias="dateTo"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=1000),
    sort_by: str = Query("recordedAt", alias="sortBy"),
    sort_order: str = Query("desc", alias="sortOrder"),
):
    result = await service.list_payments({
        "search": search, "branch_id": branch_id,
        "teacher_id": teacher_id, "module_id": module_id,
        "method": method, "payment_type": payment_type,
        "date_from": date_from, "date_to": date_to,
        "page": page, "page_size": page_size,
        "sort_by": sort_by, "sort_order": sort_order,
    }, actor)
    return {"data": result}


@router.get("/{payment_id}", summary="Get payment detail (for receipt)")
async def get_payment(
    payment_id: int,
    actor: User = Depends(require_manage_subscriptions),
    service: PaymentService = Depends(get_service),
):
    result = await service.get_payment(payment_id, actor)
    return {"data": result}
