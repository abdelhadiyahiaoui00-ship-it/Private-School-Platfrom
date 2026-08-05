from typing import Optional
from fastapi import APIRouter, Depends, Query

from src.core.database import DBSessionDep
from src.modules.auth.dependencies import CurrentUser, require_role
from src.modules.users.models import User
from src.modules.payments.service import PaymentService

router = APIRouter(prefix="/payments", tags=["Payments"])

def get_service(session: DBSessionDep) -> PaymentService:
    return PaymentService(session)

def require_manage_payments(user: User = Depends(require_role(["owner", "superAdmin", "admin"]))) -> User:
    if user.role in ("owner", "superAdmin"):
        return user
    if user.role == "admin":
        perms = user.permissions or {}
        if perms.get("managePayments"):
            return user
    from src.core.exceptions import PermissionDenied
    raise PermissionDenied(message="Requires managePayments permission.")

@router.get("", summary="List payments")
async def list_payments(
    actor: User = Depends(require_manage_payments),
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
    page_size: int = Query(20, alias="pageSize", ge=1, le=100),
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

@router.get("/summary", summary="Get payments summary")
async def get_summary(
    actor: User = Depends(require_manage_payments),
    service: PaymentService = Depends(get_service),
    branch_id: Optional[int] = Query(None, alias="branchId"),
    teacher_id: Optional[int] = Query(None, alias="teacherId"),
    module_id: Optional[int] = Query(None, alias="moduleId"),
    method: Optional[str] = Query(None),
    payment_type: Optional[str] = Query(None, alias="paymentType"),
    date_from: Optional[str] = Query(None, alias="dateFrom"),
    date_to: Optional[str] = Query(None, alias="dateTo"),
):
    result = await service.get_summary({
        "branch_id": branch_id, 
        "teacher_id": teacher_id, "module_id": module_id,
        "method": method, "payment_type": payment_type,
        "date_from": date_from, "date_to": date_to,
    }, actor)
    return {"data": result}

@router.get("/{payment_id}", summary="Get payment detail")
async def get_payment(
    payment_id: int,
    actor: User = Depends(require_manage_payments),
    service: PaymentService = Depends(get_service),
):
    result = await service.get_payment(payment_id, actor)
    return {"data": result}
