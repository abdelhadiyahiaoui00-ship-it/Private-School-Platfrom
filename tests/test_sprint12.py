import pytest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import src.app  # Import app to ensure all SQLAlchemy models are registered
from src.modules.analytics.exceptions import AnalyticsPeriodInvalid, AnalyticsExportEmpty
from src.modules.analytics.models import AnalyticsMonthlySnapshot
from src.modules.analytics.service import AnalyticsService
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

    # Future month raises period invalid when validated
    future_year = cur_year + 1
    with pytest.raises(AnalyticsPeriodInvalid):
        AnalyticsService._validate_period(future_year, 1)


@pytest.mark.asyncio
async def test_monthly_snapshot_open_month():
    now = datetime.now(timezone.utc)
    cur_year = now.year
    cur_month = now.month

    mock_session = AsyncMock()
    mock_pay_res = MagicMock()
    mock_pay_res.one.return_value = MagicMock(
        total_revenue=Decimal("1000.00"),
        total_commissions=Decimal("100.00"),
        net_revenue=Decimal("900.00"),
        payment_count=5,
    )

    mock_enr_res = MagicMock()
    mock_enr_res.scalar.return_value = 2

    mock_sub_res = MagicMock()
    mock_sub_res.scalar.return_value = 3

    mock_session.execute.side_effect = [
        mock_pay_res,
        mock_enr_res,
        mock_sub_res,
    ]

    service = AnalyticsService(mock_session)
    result = await service.get_monthly_snapshot(cur_year, cur_month, branch_id=1)

    assert isinstance(result, MonthlySnapshotOut)
    assert result.total_revenue == Decimal("1000.00")
    assert result.net_revenue == Decimal("900.00")
    assert result.payment_count == 5
    assert result.new_enrollments == 2
    assert result.active_subscriptions == 3

    # Session.add and session.commit must NEVER be called for an open month (Rule 1)
    mock_session.add.assert_not_called()
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_monthly_snapshot_closed_month_hit():
    mock_session = AsyncMock()
    cached_snapshot = AnalyticsMonthlySnapshot(
        id=1,
        branch_id=1,
        year=2025,
        month=1,
        total_revenue=Decimal("5000.00"),
        total_commissions=Decimal("500.00"),
        net_revenue=Decimal("4500.00"),
        payment_count=20,
        new_enrollments=10,
        active_subscriptions=15,
        created_at=datetime.now(timezone.utc),
    )

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = cached_snapshot
    mock_session.execute.return_value = mock_res

    service = AnalyticsService(mock_session)
    result = await service.get_monthly_snapshot(2025, 1, branch_id=1)

    assert result.total_revenue == Decimal("5000.00")
    # Session.add should not be called since cache hit
    mock_session.add.assert_not_called()


@pytest.mark.asyncio
async def test_monthly_snapshot_closed_month_miss_computes_and_inserts():
    mock_session = AsyncMock()

    mock_cache_res = MagicMock()
    mock_cache_res.scalar_one_or_none.return_value = None

    mock_pay_res = MagicMock()
    mock_pay_res.one.return_value = MagicMock(
        total_revenue=Decimal("3000.00"),
        total_commissions=Decimal("300.00"),
        net_revenue=Decimal("2700.00"),
        payment_count=12,
    )

    mock_enr_res = MagicMock()
    mock_enr_res.scalar.return_value = 5

    mock_sub_res = MagicMock()
    mock_sub_res.scalar.return_value = 8

    mock_session.execute.side_effect = [
        mock_cache_res,
        mock_pay_res,
        mock_enr_res,
        mock_sub_res,
    ]

    service = AnalyticsService(mock_session)
    result = await service.get_monthly_snapshot(2025, 2, branch_id=1)

    assert result.total_revenue == Decimal("3000.00")
    assert result.net_revenue == Decimal("2700.00")
    # Miss on closed month must call session.add and session.commit
    assert mock_session.add.called
    assert mock_session.commit.called


@pytest.mark.asyncio
async def test_revenue_overview_always_live():
    mock_session = AsyncMock()

    mock_pay_res = MagicMock()
    mock_pay_res.one.return_value = MagicMock(
        total_revenue=Decimal("1500.00"),
        total_commissions=Decimal("150.00"),
        net_revenue=Decimal("1350.00"),
        payment_count=7,
    )

    mock_enr_res = MagicMock()
    mock_enr_res.scalar.return_value = 1

    mock_sub_res = MagicMock()
    mock_sub_res.scalar.return_value = 2

    mock_session.execute.side_effect = [
        mock_pay_res,
        mock_enr_res,
        mock_sub_res,
    ]

    service = AnalyticsService(mock_session)
    overview = await service.get_revenue_overview(2025, 3, branch_id=2)

    assert isinstance(overview, RevenueOverviewOut)
    assert overview.total_revenue == Decimal("1500.00")
    assert overview.net_revenue == Decimal("1350.00")
    assert overview.payment_count == 7
    # Overview must never add snapshot to DB
    mock_session.add.assert_not_called()


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


@pytest.mark.asyncio
async def test_csv_export_empty_raises_exception():
    mock_session = AsyncMock()
    mock_res = MagicMock()
    mock_res.all.return_value = []
    mock_session.execute.return_value = mock_res

    service = AnalyticsService(mock_session)
    with pytest.raises(AnalyticsExportEmpty):
        await service.export_payments_csv(
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            datetime(2026, 1, 31, tzinfo=timezone.utc),
        )
