import io
from datetime import datetime, date, timedelta, timezone
from typing import List, Optional, Union

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
    StudentsTrendPoint,
    EnrollmentFunnelPoint,
    OperationsTrendPoint,
    TopTeacherOut,
    PaymentMethodBreakdownOut,
    BranchRevenueOut,
    MonthlySnapshotOut,
    TeacherSnapshotOut,
)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


def get_analytics_service(session: DBSessionDep) -> AnalyticsService:
    return AnalyticsService(session)


def parse_date_param(val: Optional[str], default: date) -> date:
    if not val:
        return default
    try:
        return datetime.fromisoformat(val.replace("Z", "+00:00")).date()
    except Exception:
        try:
            return date.fromisoformat(val[:10])
        except Exception:
            return default


# ─── Extended 4 Trend & Funnel Endpoints (Daily / Monthly Granularity Switch) ───

@router.get("/revenue-trend")
@router.get("/trend")
async def get_revenue_trend(
    dateFrom: Optional[str] = Query(None, alias="date_from"),
    dateTo: Optional[str] = Query(None, alias="date_to"),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    branch_id: Optional[int] = Query(None, alias="branchId"),
    locale: str = Query("ar", alias="lang"),
    user: User = Depends(require_role(["owner"])),
    service: AnalyticsService = Depends(get_analytics_service),
):
    df_raw = dateFrom or date_from
    dt_raw = dateTo or date_to

    today_d = date.today()
    default_from = today_d - timedelta(days=30)

    parsed_from = parse_date_param(df_raw, default_from)
    parsed_to = parse_date_param(dt_raw, today_d)

    if parsed_from > parsed_to:
        parsed_from, parsed_to = parsed_to, parsed_from

    items = await service.get_revenue_trend(parsed_from, parsed_to, branch_id, locale)
    return {"data": {"items": items}}


@router.get("/students-trend")
async def get_students_trend(
    dateFrom: Optional[str] = Query(None, alias="date_from"),
    dateTo: Optional[str] = Query(None, alias="date_to"),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    branch_id: Optional[int] = Query(None, alias="branchId"),
    locale: str = Query("ar", alias="lang"),
    user: User = Depends(require_role(["owner"])),
    service: AnalyticsService = Depends(get_analytics_service),
):
    df_raw = dateFrom or date_from
    dt_raw = dateTo or date_to

    today_d = date.today()
    default_from = today_d - timedelta(days=30)

    parsed_from = parse_date_param(df_raw, default_from)
    parsed_to = parse_date_param(dt_raw, today_d)

    if parsed_from > parsed_to:
        parsed_from, parsed_to = parsed_to, parsed_from

    items = await service.get_students_trend(parsed_from, parsed_to, branch_id, locale)
    return {"data": {"items": items}}


@router.get("/enrollment-funnel")
async def get_enrollment_funnel(
    dateFrom: Optional[str] = Query(None, alias="date_from"),
    dateTo: Optional[str] = Query(None, alias="date_to"),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    branch_id: Optional[int] = Query(None, alias="branchId"),
    locale: str = Query("ar", alias="lang"),
    user: User = Depends(require_role(["owner"])),
    service: AnalyticsService = Depends(get_analytics_service),
):
    df_raw = dateFrom or date_from
    dt_raw = dateTo or date_to

    today_d = date.today()
    default_from = today_d - timedelta(days=30)

    parsed_from = parse_date_param(df_raw, default_from)
    parsed_to = parse_date_param(dt_raw, today_d)

    if parsed_from > parsed_to:
        parsed_from, parsed_to = parsed_to, parsed_from

    items = await service.get_enrollment_funnel(parsed_from, parsed_to, branch_id, locale)
    return {"data": {"items": items}}


@router.get("/operations")
async def get_operations(
    dateFrom: Optional[str] = Query(None, alias="date_from"),
    dateTo: Optional[str] = Query(None, alias="date_to"),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    branch_id: Optional[int] = Query(None, alias="branchId"),
    locale: str = Query("ar", alias="lang"),
    user: User = Depends(require_role(["owner"])),
    service: AnalyticsService = Depends(get_analytics_service),
):
    df_raw = dateFrom or date_from
    dt_raw = dateTo or date_to

    today_d = date.today()
    default_from = today_d - timedelta(days=30)

    parsed_from = parse_date_param(df_raw, default_from)
    parsed_to = parse_date_param(dt_raw, today_d)

    if parsed_from > parsed_to:
        parsed_from, parsed_to = parsed_to, parsed_from

    items = await service.get_operations_trend(parsed_from, parsed_to, branch_id, locale)
    return {"data": {"items": items}}


# ─── Untouched Other Endpoints ───────────────────────────────────────────────

@router.get("/overview", response_model=ResponseWrapper[RevenueOverviewOut])
async def get_overview(
    year: int = Query(2026, ge=2000, le=2100),
    month: int = Query(9, ge=1, le=12),
    branch_id: Optional[int] = Query(None, alias="branchId"),
    user: User = Depends(require_role(["owner"])),
    service: AnalyticsService = Depends(get_analytics_service),
):
    overview = await service.get_revenue_overview(year, month, branch_id)
    return ResponseWrapper(data=overview)


@router.get("/revenue-by-branch")
@router.get("/branches")
async def get_branch_comparison(
    year: int = Query(2026, ge=2000, le=2100),
    month: int = Query(9, ge=1, le=12),
    user: User = Depends(require_role(["owner"])),
    service: AnalyticsService = Depends(get_analytics_service),
):
    branches = await service.get_branch_revenue_comparison(year, month)
    return {"data": {"items": branches}}


@router.get("/top-classes")
@router.get("/teachers/top")
async def get_top_teachers(
    year: int = Query(2026, ge=2000, le=2100),
    month: int = Query(9, ge=1, le=12),
    limit: int = Query(10, ge=1, le=100),
    branch_id: Optional[int] = Query(None, alias="branchId"),
    user: User = Depends(require_role(["owner"])),
    service: AnalyticsService = Depends(get_analytics_service),
):
    teachers = await service.get_top_teachers(year, month, limit, branch_id)
    return {"data": {"items": teachers}}


@router.get("/payment-methods", response_model=ResponseWrapper[List[PaymentMethodBreakdownOut]])
async def get_payment_methods(
    year: int = Query(2026, ge=2000, le=2100),
    month: int = Query(9, ge=1, le=12),
    branch_id: Optional[int] = Query(None, alias="branchId"),
    user: User = Depends(require_role(["owner"])),
    service: AnalyticsService = Depends(get_analytics_service),
):
    methods = await service.get_payment_method_breakdown(year, month, branch_id)
    return ResponseWrapper(data=methods)


@router.get("/snapshot", response_model=ResponseWrapper[MonthlySnapshotOut])
async def get_monthly_snapshot(
    year: int = Query(2026, ge=2000, le=2100),
    month: int = Query(9, ge=1, le=12),
    branch_id: Optional[int] = Query(None, alias="branchId"),
    user: User = Depends(require_role(["owner"])),
    service: AnalyticsService = Depends(get_analytics_service),
):
    snapshot = await service.get_monthly_snapshot(year, month, branch_id)
    return ResponseWrapper(data=snapshot)


@router.get("/teachers/snapshots", response_model=ResponseWrapper[List[TeacherSnapshotOut]])
async def get_teacher_snapshots(
    year: int = Query(2026, ge=2000, le=2100),
    month: int = Query(9, ge=1, le=12),
    branch_id: Optional[int] = Query(None, alias="branchId"),
    user: User = Depends(require_role(["owner"])),
    service: AnalyticsService = Depends(get_analytics_service),
):
    snapshots = await service.get_teacher_snapshots(year, month, branch_id)
    return ResponseWrapper(data=snapshots)


@router.get("/export")
async def export_payments(
    date_from: datetime = Query(...),
    date_to: datetime = Query(...),
    branch_id: Optional[int] = Query(None, alias="branchId"),
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
