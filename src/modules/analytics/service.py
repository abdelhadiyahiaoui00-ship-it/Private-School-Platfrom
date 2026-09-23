import csv
import io
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import List, Optional, Tuple, Dict, Any

from sqlalchemy import select, func, and_, or_, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.analytics.exceptions import AnalyticsPeriodInvalid, AnalyticsExportEmpty
from src.modules.analytics.models import AnalyticsMonthlySnapshot, AnalyticsTeacherMonthlySnapshot
from src.modules.analytics.schemas import (
    MonthlySnapshotOut,
    TeacherSnapshotOut,
    RevenueOverviewOut,
    TopTeacherOut,
    RevenueTrendPoint,
    PaymentMethodBreakdownOut,
    BranchRevenueOut,
    DataExportRow,
)
from src.modules.payments.models import Payment
from src.modules.enrollments.models import Enrollment
from src.modules.subscriptions.models import Subscription
from src.modules.users.models import User
from src.modules.branches.models import Branch
from src.modules.classes.models import Class
from src.modules.groups.models import Group
from src.modules.attendance.models import Attendance
from src.modules.sessions.models import Session as ClassSession


class AnalyticsService:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _get_current_year_month() -> Tuple[int, int]:
        now = datetime.now(timezone.utc)
        return now.year, now.month

    @staticmethod
    def _is_closed_month(year: int, month: int) -> bool:
        cur_year, cur_month = AnalyticsService._get_current_year_month()
        if year < cur_year:
            return True
        if year == cur_year and month < cur_month:
            return True
        return False

    @staticmethod
    def _validate_period(year: int, month: int) -> None:
        if month < 1 or month > 12:
            raise AnalyticsPeriodInvalid(message="Month must be between 1 and 12.")
        cur_year, cur_month = AnalyticsService._get_current_year_month()
        if year > cur_year or (year == cur_year and month > cur_month):
            raise AnalyticsPeriodInvalid(message="Requested period is in the future.")

    @staticmethod
    def _get_date_range(year: int, month: int) -> Tuple[datetime, datetime]:
        start_dt = datetime(year, month, 1, 0, 0, 0, tzinfo=timezone.utc)
        if month == 12:
            end_dt = datetime(year + 1, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        else:
            end_dt = datetime(year, month + 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        return start_dt, end_dt

    async def _compute_live_monthly_metrics(
        self, year: int, month: int, branch_id: Optional[int] = None
    ) -> Dict[str, Any]:
        start_dt, end_dt = self._get_date_range(year, month)

        # Payments summary
        pay_stmt = select(
            func.coalesce(func.sum(Payment.amount), 0).label("total_revenue"),
            func.coalesce(func.sum(Payment.commission_amount), 0).label("total_commissions"),
            func.coalesce(func.sum(Payment.net_amount), 0).label("net_revenue"),
            func.count(Payment.id).label("payment_count"),
        ).where(
            and_(
                Payment.recorded_at >= start_dt,
                Payment.recorded_at < end_dt,
            )
        )
        if branch_id is not None:
            pay_stmt = pay_stmt.where(Payment.branch_id == branch_id)

        res = await self.session.execute(pay_stmt)
        pay_res = res.one()

        # New enrollments count
        enr_stmt = select(func.count(Enrollment.id)).where(
            and_(
                Enrollment.created_at >= start_dt,
                Enrollment.created_at < end_dt,
            )
        )
        if branch_id is not None:
            enr_stmt = enr_stmt.where(Enrollment.branch_id == branch_id)
        res_enr = await self.session.execute(enr_stmt)
        new_enrollments = res_enr.scalar() or 0

        # Active subscriptions count
        sub_stmt = select(func.count(Subscription.id)).where(
            and_(
                Subscription.created_at >= start_dt,
                Subscription.created_at < end_dt,
            )
        )
        if branch_id is not None:
            sub_stmt = sub_stmt.where(Subscription.branch_id == branch_id)
        res_sub = await self.session.execute(sub_stmt)
        active_subscriptions = res_sub.scalar() or 0

        return {
            "year": year,
            "month": month,
            "branch_id": branch_id,
            "total_revenue": Decimal(str(pay_res.total_revenue)),
            "total_commissions": Decimal(str(pay_res.total_commissions)),
            "net_revenue": Decimal(str(pay_res.net_revenue)),
            "payment_count": int(pay_res.payment_count),
            "new_enrollments": int(new_enrollments),
            "active_subscriptions": int(active_subscriptions),
        }

    async def get_revenue_overview(
        self, year: int, month: int, branch_id: Optional[int] = None
    ) -> RevenueOverviewOut:
        self._validate_period(year, month)
        # Always computed live as per Rule 4
        metrics = await self._compute_live_monthly_metrics(year, month, branch_id)
        return RevenueOverviewOut(
            total_revenue=metrics["total_revenue"],
            total_commissions=metrics["total_commissions"],
            net_revenue=metrics["net_revenue"],
            payment_count=metrics["payment_count"],
            year=year,
            month=month,
            branch_id=branch_id,
        )

    async def get_monthly_snapshot(
        self, year: int, month: int, branch_id: Optional[int] = None
    ) -> MonthlySnapshotOut:
        self._validate_period(year, month)
        is_closed = self._is_closed_month(year, month)

        if not is_closed:
            # Open month: compute live, do not cache
            metrics = await self._compute_live_monthly_metrics(year, month, branch_id)
            return MonthlySnapshotOut(**metrics)

        # Closed month: lazy cache lookup
        stmt = select(AnalyticsMonthlySnapshot).where(
            and_(
                AnalyticsMonthlySnapshot.year == year,
                AnalyticsMonthlySnapshot.month == month,
                (
                    AnalyticsMonthlySnapshot.branch_id == branch_id
                    if branch_id is not None
                    else AnalyticsMonthlySnapshot.branch_id.is_(None)
                ),
            )
        )
        res = await self.session.execute(stmt)
        result = res.scalar_one_or_none()

        if result:
            return MonthlySnapshotOut.model_validate(result)

        # Miss: Compute once, INSERT, return
        metrics = await self._compute_live_monthly_metrics(year, month, branch_id)
        snapshot = AnalyticsMonthlySnapshot(
            branch_id=branch_id,
            year=year,
            month=month,
            total_revenue=metrics["total_revenue"],
            total_commissions=metrics["total_commissions"],
            net_revenue=metrics["net_revenue"],
            payment_count=metrics["payment_count"],
            new_enrollments=metrics["new_enrollments"],
            active_subscriptions=metrics["active_subscriptions"],
        )
        self.session.add(snapshot)
        await self.session.commit()
        await self.session.refresh(snapshot)
        return MonthlySnapshotOut.model_validate(snapshot)

    async def get_revenue_trend(
        self, months_back: int = 12, branch_id: Optional[int] = None
    ) -> List[RevenueTrendPoint]:
        cur_year, cur_month = self._get_current_year_month()
        trend_points: List[RevenueTrendPoint] = []

        target_months = []
        y, m = cur_year, cur_month
        for _ in range(months_back):
            target_months.append((y, m))
            m -= 1
            if m < 1:
                m = 12
                y -= 1
        target_months.reverse()

        for yr, mo in target_months:
            snapshot = await self.get_monthly_snapshot(yr, mo, branch_id)
            trend_points.append(
                RevenueTrendPoint(
                    year=yr,
                    month=mo,
                    total_revenue=snapshot.total_revenue,
                    net_revenue=snapshot.net_revenue,
                    payment_count=snapshot.payment_count,
                )
            )

        return trend_points

    async def get_top_teachers(
        self, year: int, month: int, limit: int = 10, branch_id: Optional[int] = None
    ) -> List[TopTeacherOut]:
        self._validate_period(year, month)
        start_dt, end_dt = self._get_date_range(year, month)

        stmt = (
            select(
                Payment.teacher_id,
                User.first_name,
                User.last_name,
                func.coalesce(func.sum(Payment.amount), 0).label("total_revenue"),
                func.coalesce(func.sum(Payment.net_amount), 0).label("net_revenue"),
                func.count(Payment.id).label("payment_count"),
            )
            .join(User, User.id == Payment.teacher_id)
            .where(
                and_(
                    Payment.recorded_at >= start_dt,
                    Payment.recorded_at < end_dt,
                    Payment.teacher_id.isnot(None),
                )
            )
            .group_by(Payment.teacher_id, User.first_name, User.last_name)
            .order_by(text("total_revenue DESC"))
            .limit(limit)
        )

        if branch_id is not None:
            stmt = stmt.where(Payment.branch_id == branch_id)

        res = await self.session.execute(stmt)
        rows = res.all()
        result = []
        for r in rows:
            name = f"{r.first_name} {r.last_name}".strip()
            result.append(
                TopTeacherOut(
                    teacher_id=r.teacher_id,
                    teacher_name=name,
                    total_revenue=Decimal(str(r.total_revenue)),
                    net_revenue=Decimal(str(r.net_revenue)),
                    payment_count=int(r.payment_count),
                )
            )
        return result

    async def get_payment_method_breakdown(
        self, year: int, month: int, branch_id: Optional[int] = None
    ) -> List[PaymentMethodBreakdownOut]:
        self._validate_period(year, month)
        start_dt, end_dt = self._get_date_range(year, month)

        stmt = select(
            Payment.method,
            func.count(Payment.id).label("count"),
            func.coalesce(func.sum(Payment.amount), 0).label("total_amount"),
        ).where(
            and_(
                Payment.recorded_at >= start_dt,
                Payment.recorded_at < end_dt,
            )
        ).group_by(Payment.method)

        if branch_id is not None:
            stmt = stmt.where(Payment.branch_id == branch_id)

        res = await self.session.execute(stmt)
        rows = res.all()
        grand_total = sum(Decimal(str(r.total_amount)) for r in rows)

        result = []
        for r in rows:
            amt = Decimal(str(r.total_amount))
            pct = float((amt / grand_total) * 100) if grand_total > 0 else 0.0
            result.append(
                PaymentMethodBreakdownOut(
                    method=r.method,
                    count=int(r.count),
                    total_amount=amt,
                    percentage=round(pct, 2),
                )
            )
        return result

    async def get_branch_revenue_comparison(
        self, year: int, month: int
    ) -> List[BranchRevenueOut]:
        self._validate_period(year, month)
        start_dt, end_dt = self._get_date_range(year, month)

        stmt = (
            select(
                Payment.branch_id,
                Branch.name.label("branch_name"),
                func.coalesce(func.sum(Payment.amount), 0).label("total_revenue"),
                func.coalesce(func.sum(Payment.net_amount), 0).label("net_revenue"),
                func.count(Payment.id).label("payment_count"),
            )
            .join(Branch, Branch.id == Payment.branch_id)
            .where(
                and_(
                    Payment.recorded_at >= start_dt,
                    Payment.recorded_at < end_dt,
                )
            )
            .group_by(Payment.branch_id, Branch.name)
            .order_by(text("total_revenue DESC"))
        )

        res = await self.session.execute(stmt)
        rows = res.all()
        return [
            BranchRevenueOut(
                branch_id=r.branch_id,
                branch_name=r.branch_name,
                total_revenue=Decimal(str(r.total_revenue)),
                net_revenue=Decimal(str(r.net_revenue)),
                payment_count=int(r.payment_count),
            )
            for r in rows
        ]

    async def get_teacher_snapshots(
        self, year: int, month: int, branch_id: Optional[int] = None
    ) -> List[TeacherSnapshotOut]:
        self._validate_period(year, month)
        is_closed = self._is_closed_month(year, month)

        if is_closed:
            stmt = select(AnalyticsTeacherMonthlySnapshot).where(
                and_(
                    AnalyticsTeacherMonthlySnapshot.year == year,
                    AnalyticsTeacherMonthlySnapshot.month == month,
                    (
                        AnalyticsTeacherMonthlySnapshot.branch_id == branch_id
                        if branch_id is not None
                        else AnalyticsTeacherMonthlySnapshot.branch_id.is_(None)
                    ),
                )
            )
            res = await self.session.execute(stmt)
            cached = res.scalars().all()
            if cached:
                return [TeacherSnapshotOut.model_validate(c) for c in cached]

        start_dt, end_dt = self._get_date_range(year, month)

        stmt = (
            select(
                Payment.teacher_id,
                func.coalesce(func.sum(Payment.amount), 0).label("total_revenue"),
                func.coalesce(func.sum(Payment.commission_amount), 0).label("total_commissions"),
                func.coalesce(func.sum(Payment.net_amount), 0).label("net_revenue"),
                func.count(Payment.id).label("payment_count"),
            )
            .where(
                and_(
                    Payment.recorded_at >= start_dt,
                    Payment.recorded_at < end_dt,
                    Payment.teacher_id.isnot(None),
                )
            )
            .group_by(Payment.teacher_id)
        )
        if branch_id is not None:
            stmt = stmt.where(Payment.branch_id == branch_id)

        res = await self.session.execute(stmt)
        rows = res.all()

        result = []
        for r in rows:
            t_id = r.teacher_id
            sess_stmt = select(func.count(ClassSession.id)).join(Group, Group.id == ClassSession.group_id).where(
                and_(
                    ClassSession.session_date >= start_dt.date(),
                    ClassSession.session_date < end_dt.date(),
                )
            )
            res_sess = await self.session.execute(sess_stmt)
            sess_cnt = res_sess.scalar() or 0

            stu_stmt = select(func.count(func.distinct(Payment.student_id))).where(
                and_(
                    Payment.teacher_id == t_id,
                    Payment.recorded_at >= start_dt,
                    Payment.recorded_at < end_dt,
                )
            )
            res_stu = await self.session.execute(stu_stmt)
            stu_cnt = res_stu.scalar() or 0

            data = {
                "teacher_id": t_id,
                "branch_id": branch_id,
                "year": year,
                "month": month,
                "total_revenue": Decimal(str(r.total_revenue)),
                "total_commissions": Decimal(str(r.total_commissions)),
                "net_revenue": Decimal(str(r.net_revenue)),
                "session_count": int(sess_cnt),
                "student_count": int(stu_cnt),
                "payment_count": int(r.payment_count),
            }

            if is_closed:
                snap = AnalyticsTeacherMonthlySnapshot(**data)
                self.session.add(snap)

            result.append(TeacherSnapshotOut(**data))

        if is_closed and result:
            await self.session.commit()

        return result

    async def export_payments_csv(
        self,
        date_from: datetime,
        date_to: datetime,
        branch_id: Optional[int] = None,
    ) -> str:
        stmt = (
            select(
                Payment.id.label("payment_id"),
                Payment.student_id,
                User.first_name.label("student_first_name"),
                User.last_name.label("student_last_name"),
                Payment.branch_id,
                Branch.name.label("branch_name"),
                Payment.class_id,
                Class.name.label("class_name"),
                Payment.teacher_id,
                Payment.amount,
                Payment.commission_amount,
                Payment.net_amount,
                Payment.method,
                Payment.payment_type,
                Payment.recorded_at,
            )
            .join(User, User.id == Payment.student_id)
            .join(Branch, Branch.id == Payment.branch_id)
            .outerjoin(Class, Class.id == Payment.class_id)
            .where(
                and_(
                    Payment.recorded_at >= date_from,
                    Payment.recorded_at <= date_to,
                )
            )
            .order_by(Payment.recorded_at.desc())
        )

        if branch_id is not None:
            stmt = stmt.where(Payment.branch_id == branch_id)

        res = await self.session.execute(stmt)
        rows = res.all()

        if not rows:
            raise AnalyticsExportEmpty()

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow([
            "Payment ID",
            "Student ID",
            "Student Name",
            "Branch ID",
            "Branch Name",
            "Class ID",
            "Class Name",
            "Teacher ID",
            "Amount",
            "Commission Amount",
            "Net Amount",
            "Method",
            "Payment Type",
            "Recorded At",
        ])

        for r in rows:
            student_name = f"{r.student_first_name} {r.student_last_name}".strip()
            writer.writerow([
                r.payment_id,
                r.student_id,
                student_name,
                r.branch_id,
                r.branch_name,
                r.class_id or "",
                r.class_name or "",
                r.teacher_id or "",
                f"{r.amount:.2f}",
                f"{r.commission_amount:.2f}",
                f"{r.net_amount:.2f}",
                r.method,
                r.payment_type,
                r.recorded_at.isoformat() if r.recorded_at else "",
            ])

        return output.getvalue()
