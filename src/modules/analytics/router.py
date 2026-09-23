import io
from datetime import datetime, date
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from src.core.database import DBSessionDep
from src.modules.auth.dependencies import require_role
from src.modules.users.models import User
from src.modules.analytics.service import AnalyticsService
from src.modules.analytics.schemas import (
    ResponseWrapper,
    RevenueOverviewOut,
    RevenueTrendPoint,
    TopTeacherOut,
    PaymentMethodBreakdownOut,
    BranchRevenueOut,
    MonthlySnapshotOut,
    TeacherSnapshotOut,
)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


def get_analytics_service(session: DBSessionDep) -> AnalyticsService:
    return AnalyticsService(session)


@router.get("/overview", response_model=ResponseWrapper[RevenueOverviewOut])
async def get_overview(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    branch_id: Optional[int] = Query(None),
    user: User = Depends(require_role(["owner"])),
    service: AnalyticsService = Depends(get_analytics_service),
):
    overview = await service.get_revenue_overview(year, month, branch_id)
    return ResponseWrapper(data=overview)


@router.get("/trend", response_model=ResponseWrapper[List[RevenueTrendPoint]])
async def get_trend(
    months_back: int = Query(12, ge=1, le=36),
    branch_id: Optional[int] = Query(None),
    user: User = Depends(require_role(["owner"])),
    service: AnalyticsService = Depends(get_analytics_service),
):
    trend = await service.get_revenue_trend(months_back, branch_id)
    return ResponseWrapper(data=trend)


@router.get("/teachers/top", response_model=ResponseWrapper[List[TopTeacherOut]])
async def get_top_teachers(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    limit: int = Query(10, ge=1, le=100),
    branch_id: Optional[int] = Query(None),
    user: User = Depends(require_role(["owner"])),
    service: AnalyticsService = Depends(get_analytics_service),
):
    teachers = await service.get_top_teachers(year, month, limit, branch_id)
    return ResponseWrapper(data=teachers)


@router.get("/payment-methods", response_model=ResponseWrapper[List[PaymentMethodBreakdownOut]])
async def get_payment_methods(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    branch_id: Optional[int] = Query(None),
    user: User = Depends(require_role(["owner"])),
    service: AnalyticsService = Depends(get_analytics_service),
):
    methods = await service.get_payment_method_breakdown(year, month, branch_id)
    return ResponseWrapper(data=methods)


@router.get("/branches", response_model=ResponseWrapper[List[BranchRevenueOut]])
async def get_branch_comparison(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    user: User = Depends(require_role(["owner"])),
    service: AnalyticsService = Depends(get_analytics_service),
):
    branches = await service.get_branch_revenue_comparison(year, month)
    return ResponseWrapper(data=branches)


@router.get("/snapshot", response_model=ResponseWrapper[MonthlySnapshotOut])
async def get_monthly_snapshot(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    branch_id: Optional[int] = Query(None),
    user: User = Depends(require_role(["owner"])),
    service: AnalyticsService = Depends(get_analytics_service),
):
    snapshot = await service.get_monthly_snapshot(year, month, branch_id)
    return ResponseWrapper(data=snapshot)


@router.get("/teachers/snapshots", response_model=ResponseWrapper[List[TeacherSnapshotOut]])
async def get_teacher_snapshots(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    branch_id: Optional[int] = Query(None),
    user: User = Depends(require_role(["owner"])),
    service: AnalyticsService = Depends(get_analytics_service),
):
    snapshots = await service.get_teacher_snapshots(year, month, branch_id)
    return ResponseWrapper(data=snapshots)


@router.get("/export")
async def export_payments(
    date_from: datetime = Query(...),
    date_to: datetime = Query(...),
    branch_id: Optional[int] = Query(None),
    user: User = Depends(require_role(["owner"])),
    service: AnalyticsService = Depends(get_analytics_service),
):
    csv_data = await service.export_payments_csv(date_from, date_to, branch_id)
    filename = f"payments_export_{date_from.strftime('%Y%m%d')}_to_{date_to.strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        io.BytesIO(csv_data.encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
