import pytest
from datetime import datetime, date, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import src.app  # Import app to ensure all SQLAlchemy models are registered
from src.modules.analytics.exceptions import AnalyticsPeriodInvalid, AnalyticsExportEmpty
from src.modules.analytics.models import AnalyticsMonthlySnapshot
from src.modules.analytics.service import AnalyticsService, format_analytics_label
from src.modules.analytics.schemas import (
    RevenueOverviewOut,
    MonthlySnapshotOut,
)


def test_is_closed_month_logic():
    now = datetime.now(timezone.utc)
    cur_year = now.year
    cur_month = now.month

    # Current month is NOT closed
    assert AnalyticsService._is_closed_month(cur_year, cur_month) is False

    # Past month is closed
    if cur_month > 1:
        assert AnalyticsService._is_closed_month(cur_year, cur_month - 1) is True
    else:
        assert AnalyticsService._is_closed_month(cur_year - 1, 12) is True


def test_format_analytics_label():
    # Arabic daily & monthly
    lbl_ar_day = format_analytics_label(2026, 9, 14, "day", "ar")
    assert lbl_ar_day == "14 سبتمبر 2026"

    lbl_ar_month = format_analytics_label(2026, 9, None, "month", "ar")
    assert lbl_ar_month == "سبتمبر 2026"

    # French daily
    lbl_fr_day = format_analytics_label(2026, 9, 14, "day", "fr")
    assert lbl_fr_day == "14 septembre 2026"

    # English daily
    lbl_en_day = format_analytics_label(2026, 9, 14, "day", "en")
    assert lbl_en_day == "14 September 2026"


@pytest.mark.asyncio
async def test_revenue_trend_daily_mode():
    mock_session = AsyncMock()

    mock_pay_res = MagicMock()
    mock_pay_res.one.return_value = MagicMock(
        total_revenue=Decimal("500.00"),
        commission_total=Decimal("50.00"),
        net_revenue=Decimal("450.00"),
        payments_count=2,
    )
    mock_session.execute.return_value = mock_pay_res

    service = AnalyticsService(mock_session)
    d_from = date(2026, 9, 1)
    d_to = date(2026, 9, 5)  # 5 days inclusive <= 31

    points = await service.get_revenue_trend(d_from, d_to, branch_id=1, locale="ar")

    assert len(points) == 5
    for i, pt in enumerate(points, start=1):
        assert pt["granularity"] == "day"
        assert pt["day"] == i
        assert pt["month"] == 9
        assert pt["year"] == 2026
        assert pt["label"] == f"{i} سبتمبر 2026"
        assert pt["isFinal"] is True  # 2026-09-01..05 is strictly before 2026-09-23


@pytest.mark.asyncio
async def test_revenue_trend_monthly_mode():
    mock_session = AsyncMock()

    mock_cache_res = MagicMock()
    mock_cache_res.scalar_one_or_none.return_value = None

    mock_pay_res = MagicMock()
    mock_pay_res.one.return_value = MagicMock(
        total_revenue=Decimal("10000.00"),
        total_commissions=Decimal("1000.00"),
        net_revenue=Decimal("9000.00"),
        payment_count=40,
    )

    mock_enr_res = MagicMock()
    mock_enr_res.scalar.return_value = 10

    mock_sub_res = MagicMock()
    mock_sub_res.scalar.return_value = 15

    # Executes for get_monthly_snapshot cache check + live compute for 2 months
    mock_session.execute.side_effect = [
        mock_cache_res, mock_pay_res, mock_enr_res, mock_sub_res,
        mock_cache_res, mock_pay_res, mock_enr_res, mock_sub_res,
    ]

    service = AnalyticsService(mock_session)
    d_from = date(2026, 1, 1)
    d_to = date(2026, 2, 28)  # 59 days > 31 → Monthly mode

    points = await service.get_revenue_trend(d_from, d_to, branch_id=1, locale="ar")

    assert len(points) == 2
    assert points[0]["granularity"] == "month"
    assert points[0]["day"] is None
    assert points[0]["label"] == "جانفي 2026"

    assert points[1]["granularity"] == "month"
    assert points[1]["day"] is None
    assert points[1]["label"] == "فيفري 2026"


@pytest.mark.asyncio
async def test_students_trend_daily_mode():
    mock_session = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar.return_value = 25
    mock_session.execute.return_value = mock_res

    service = AnalyticsService(mock_session)
    d_from = date(2026, 9, 10)
    d_to = date(2026, 9, 12)  # 3 days <= 31

    points = await service.get_students_trend(d_from, d_to, branch_id=None, locale="ar")

    assert len(points) == 3
    assert points[0]["granularity"] == "day"
    assert points[0]["day"] == 10
    assert points[0]["activeStudentsCount"] == 25


@pytest.mark.asyncio
async def test_enrollment_funnel_daily_mode():
    mock_session = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar.return_value = 10
    mock_session.execute.return_value = mock_res

    service = AnalyticsService(mock_session)
    d_from = date(2026, 9, 14)
    d_to = date(2026, 9, 14)  # 1 day <= 31

    points = await service.get_enrollment_funnel(d_from, d_to, branch_id=None, locale="ar")

    assert len(points) == 1
    pt = points[0]
    assert pt["granularity"] == "day"
    assert pt["day"] == 14
    assert pt["label"] == "14 سبتمبر 2026"
    assert "visitorRequestsCount" in pt
    assert "enrollmentsCreatedCount" in pt


@pytest.mark.asyncio
async def test_operations_trend_daily_mode():
    mock_session = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar.return_value = 3
    mock_session.execute.return_value = mock_res

    service = AnalyticsService(mock_session)
    d_from = date(2026, 9, 15)
    d_to = date(2026, 9, 16)  # 2 days <= 31

    points = await service.get_operations_trend(d_from, d_to, branch_id=None, locale="ar")

    assert len(points) == 2
    assert points[0]["granularity"] == "day"
    assert points[0]["day"] == 15
    assert points[0]["teacherAbsencesCount"] == 3
    assert points[0]["reschedulesApprovedCount"] == 3


@pytest.mark.asyncio
async def test_csv_export_format():
    mock_session = AsyncMock()

    row1 = MagicMock()
    row1.payment_id = 101
    row1.student_id = 5
    row1.student_first_name = "Ahmed"
    row1.student_last_name = "Benali"
    row1.branch_id = 1
    row1.branch_name = "Main Branch"
    row1.class_id = 20
    row1.class_name = "Math 101"
    row1.teacher_id = 3
    row1.amount = Decimal("2500.00")
    row1.commission_amount = Decimal("250.00")
    row1.net_amount = Decimal("2250.00")
    row1.method = "cash"
    row1.payment_type = "initial"
    row1.recorded_at = datetime(2026, 9, 15, 10, 0, 0, tzinfo=timezone.utc)

    mock_res = MagicMock()
    mock_res.all.return_value = [row1]
    mock_session.execute.return_value = mock_res

    service = AnalyticsService(mock_session)
    csv_text = await service.export_payments_csv(
        datetime(2026, 9, 1, tzinfo=timezone.utc),
        datetime(2026, 9, 30, tzinfo=timezone.utc),
        branch_id=1,
    )

    assert "Payment ID,Student ID,Student Name" in csv_text
    assert "101,5,Ahmed Benali,1,Main Branch,20,Math 101,3,2500.00,250.00,2250.00,cash,initial" in csv_text
