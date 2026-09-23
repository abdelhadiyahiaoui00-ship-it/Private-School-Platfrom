import csv
import io
from datetime import datetime, date, time, timezone, timedelta
from decimal import Decimal
from typing import List, Optional, Tuple, Dict, Any, Union

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
    StudentsTrendPoint,
    EnrollmentFunnelPoint,
    OperationsTrendPoint,
    PaymentMethodBreakdownOut,
    BranchRevenueOut,
    DataExportRow,
)
from src.modules.payments.models import Payment
from src.modules.enrollments.models import Enrollment
from src.modules.enrollments.visitor_models import VisitorEnrollmentRequest
from src.modules.subscriptions.models import Subscription
from src.modules.users.models import User
from src.modules.branches.models import Branch
from src.modules.classes.models import Class
from src.modules.groups.models import Group
from src.modules.attendance.models import Attendance
from src.modules.sessions.models import Session as ClassSession


ARABIC_MONTHS = [
    "جانفي", "فيفري", "مارس", "أفريل", "ماي", "جوان",
    "جويلية", "أوت", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"
]

FRENCH_MONTHS = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre"
]

ENGLISH_MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]


def format_analytics_label(year: int, month: int, day: Optional[int], granularity: str, locale: str = "ar") -> str:
    loc = (locale or "ar").lower().strip()
    if loc.startswith("fr"):
        month_name = FRENCH_MONTHS[month - 1]
    elif loc.startswith("en"):
        month_name = ENGLISH_MONTHS[month - 1]
    else:
        month_name = ARABIC_MONTHS[month - 1]

    if granularity == "day" and day is not None:
        return f"{day} {month_name} {year}"
    return f"{month_name} {year}"


def check_is_final(target_date: date, granularity: str) -> bool:
    today = date.today()
    if granularity == "day":
        return target_date < today
    else:
        if target_date.year < today.year:
            return True
        if target_date.year == today.year and target_date.month < today.month:
            return True
        return False


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

    @staticmethod
    def _get_date_range(year: int, month: int) -> Tuple[datetime, datetime]:
        start_dt = datetime(year, month, 1, 0, 0, 0, tzinfo=timezone.utc)
        if month == 12:
            end_dt = datetime(year + 1, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        else:
            end_dt = datetime(year, month + 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        return start_dt, end_dt

    def _get_months_in_range(self, date_from: date, date_to: date) -> List[Tuple[int, int]]:
        months = []
        cur_year, cur_month = date_from.year, date_from.month
        end_year, end_month = date_to.year, date_to.month

        while (cur_year, cur_month) <= (end_year, end_month):
            months.append((cur_year, cur_month))
            cur_month += 1
            if cur_month > 12:
                cur_month = 1
                cur_year += 1
        return months

    async def _compute_live_monthly_metrics(
        self, year: int, month: int, branch_id: Optional[int] = None
    ) -> Dict[str, Any]:
        start_dt, end_dt = self._get_date_range(year, month)

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
            metrics = await self._compute_live_monthly_metrics(year, month, branch_id)
            return MonthlySnapshotOut(**metrics)

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

    # ─── Granularity Routing Endpoints ─────────────────────────────────────────

    async def get_revenue_trend(
        self,
        date_from: date,
        date_to: date,
        branch_id: Optional[int] = None,
        locale: str = "ar",
    ) -> List[Dict[str, Any]]:
        days_inclusive = (date_to - date_from).days + 1
        points: List[Dict[str, Any]] = []

        if days_inclusive <= 31:
            # Daily mode
            cur = date_from
            today_d = date.today()
            while cur <= date_to:
                start_dt = datetime.combine(cur, time.min, tzinfo=timezone.utc)
                end_dt = datetime.combine(cur + timedelta(days=1), time.min, tzinfo=timezone.utc)

                stmt = select(
                    func.coalesce(func.sum(Payment.amount), 0).label("total_revenue"),
                    func.coalesce(func.sum(Payment.commission_amount), 0).label("commission_total"),
                    func.coalesce(func.sum(Payment.net_amount), 0).label("net_revenue"),
                    func.count(Payment.id).label("payments_count"),
                ).where(
                    and_(
                        Payment.recorded_at >= start_dt,
                        Payment.recorded_at < end_dt,
                    )
                )
                if branch_id is not None:
                    stmt = stmt.where(Payment.branch_id == branch_id)

                res = await self.session.execute(stmt)
                r = res.one()

                is_final_flag = cur < today_d
                label_str = format_analytics_label(cur.year, cur.month, cur.day, "day", locale)

                tot_rev = Decimal(str(r.total_revenue))
                comm_tot = Decimal(str(r.commission_total))
                net_rev = Decimal(str(r.net_revenue))
                pay_cnt = int(r.payments_count)

                points.append({
                    "granularity": "day",
                    "day": cur.day,
                    "isFinal": is_final_flag,
                    "is_final": is_final_flag,
                    "label": label_str,
                    "year": cur.year,
                    "month": cur.month,
                    "totalRevenue": tot_rev,
                    "total_revenue": tot_rev,
                    "commissionTotal": comm_tot,
                    "commission_total": comm_tot,
                    "netRevenue": net_rev,
                    "net_revenue": net_rev,
                    "paymentsCount": pay_cnt,
                    "payment_count": pay_cnt,
                })
                cur += timedelta(days=1)
        else:
            # Monthly mode
            months = self._get_months_in_range(date_from, date_to)
            today_d = date.today()
            for yr, mo in months:
                snapshot = await self.get_monthly_snapshot(yr, mo, branch_id)
                target_date = date(yr, mo, 1)
                is_final_flag = check_is_final(target_date, "month")
                label_str = format_analytics_label(yr, mo, None, "month", locale)

                points.append({
                    "granularity": "month",
                    "day": None,
                    "isFinal": is_final_flag,
                    "is_final": is_final_flag,
                    "label": label_str,
                    "year": yr,
                    "month": mo,
                    "totalRevenue": snapshot.total_revenue,
                    "total_revenue": snapshot.total_revenue,
                    "commissionTotal": snapshot.total_commissions,
                    "commission_total": snapshot.total_commissions,
                    "netRevenue": snapshot.net_revenue,
                    "net_revenue": snapshot.net_revenue,
                    "paymentsCount": snapshot.payment_count,
                    "payment_count": snapshot.payment_count,
                })

        return points

    async def get_students_trend(
        self,
        date_from: date,
        date_to: date,
        branch_id: Optional[int] = None,
        locale: str = "ar",
    ) -> List[Dict[str, Any]]:
        days_inclusive = (date_to - date_from).days + 1
        points: List[Dict[str, Any]] = []

        if days_inclusive <= 31:
            cur = date_from
            today_d = date.today()
            while cur <= date_to:
                stmt = select(func.count(func.distinct(Subscription.student_id))).where(
                    and_(
                        Subscription.status == "active",
                        Subscription.start_date <= cur,
                        Subscription.end_date >= cur,
                    )
                )
                if branch_id is not None:
                    stmt = stmt.where(Subscription.branch_id == branch_id)

                res = await self.session.execute(stmt)
                cnt = res.scalar() or 0

                is_final_flag = cur < today_d
                label_str = format_analytics_label(cur.year, cur.month, cur.day, "day", locale)

                points.append({
                    "granularity": "day",
                    "day": cur.day,
                    "isFinal": is_final_flag,
                    "is_final": is_final_flag,
                    "label": label_str,
                    "year": cur.year,
                    "month": cur.month,
                    "activeStudentsCount": int(cnt),
                    "active_students_count": int(cnt),
                })
                cur += timedelta(days=1)
        else:
            months = self._get_months_in_range(date_from, date_to)
            for yr, mo in months:
                start_d = date(yr, mo, 1)
                if mo == 12:
                    end_d = date(yr + 1, 1, 1) - timedelta(days=1)
                else:
                    end_d = date(yr, mo + 1, 1) - timedelta(days=1)

                stmt = select(func.count(func.distinct(Subscription.student_id))).where(
                    and_(
                        Subscription.status == "active",
                        Subscription.start_date <= end_d,
                        Subscription.end_date >= start_d,
                    )
                )
                if branch_id is not None:
                    stmt = stmt.where(Subscription.branch_id == branch_id)

                res = await self.session.execute(stmt)
                cnt = res.scalar() or 0

                is_final_flag = check_is_final(start_d, "month")
                label_str = format_analytics_label(yr, mo, None, "month", locale)

                points.append({
                    "granularity": "month",
                    "day": None,
                    "isFinal": is_final_flag,
                    "is_final": is_final_flag,
                    "label": label_str,
                    "year": yr,
                    "month": mo,
                    "activeStudentsCount": int(cnt),
                    "active_students_count": int(cnt),
                })

        return points

    async def get_enrollment_funnel(
        self,
        date_from: date,
        date_to: date,
        branch_id: Optional[int] = None,
        locale: str = "ar",
    ) -> List[Dict[str, Any]]:
        days_inclusive = (date_to - date_from).days + 1
        points: List[Dict[str, Any]] = []

        if days_inclusive <= 31:
            cur = date_from
            today_d = date.today()
            while cur <= date_to:
                start_dt = datetime.combine(cur, time.min, tzinfo=timezone.utc)
                end_dt = datetime.combine(cur + timedelta(days=1), time.min, tzinfo=timezone.utc)

                vis_stmt = select(func.count(VisitorEnrollmentRequest.id)).where(
                    and_(
                        VisitorEnrollmentRequest.created_at >= start_dt,
                        VisitorEnrollmentRequest.created_at < end_dt,
                    )
                )
                vis_cnt = (await self.session.execute(vis_stmt)).scalar() or 0

                vis_conv_stmt = select(func.count(VisitorEnrollmentRequest.id)).where(
                    and_(
                        VisitorEnrollmentRequest.created_at >= start_dt,
                        VisitorEnrollmentRequest.created_at < end_dt,
                        VisitorEnrollmentRequest.status == "converted",
                    )
                )
                vis_conv_cnt = (await self.session.execute(vis_conv_stmt)).scalar() or 0

                enr_created_stmt = select(func.count(Enrollment.id)).where(
                    and_(
                        Enrollment.created_at >= start_dt,
                        Enrollment.created_at < end_dt,
                    )
                )
                if branch_id is not None:
                    enr_created_stmt = enr_created_stmt.where(Enrollment.branch_id == branch_id)
                enr_created_cnt = (await self.session.execute(enr_created_stmt)).scalar() or 0

                enr_active_stmt = select(func.count(Enrollment.id)).where(
                    and_(
                        Enrollment.status == "active",
                        or_(
                            and_(Enrollment.activated_at >= start_dt, Enrollment.activated_at < end_dt),
                            and_(Enrollment.created_at >= start_dt, Enrollment.created_at < end_dt),
                        )
                    )
                )
                if branch_id is not None:
                    enr_active_stmt = enr_active_stmt.where(Enrollment.branch_id == branch_id)
                enr_active_cnt = (await self.session.execute(enr_active_stmt)).scalar() or 0

                rate = float((vis_conv_cnt / vis_cnt) * 100) if vis_cnt > 0 else 0.0

                is_final_flag = cur < today_d
                label_str = format_analytics_label(cur.year, cur.month, cur.day, "day", locale)

                points.append({
                    "granularity": "day",
                    "day": cur.day,
                    "isFinal": is_final_flag,
                    "is_final": is_final_flag,
                    "label": label_str,
                    "year": cur.year,
                    "month": cur.month,
                    "visitorRequestsCount": int(vis_cnt),
                    "visitor_requests_count": int(vis_cnt),
                    "visitorRequestsConvertedCount": int(vis_conv_cnt),
                    "visitor_requests_converted_count": int(vis_conv_cnt),
                    "enrollmentsCreatedCount": int(enr_created_cnt),
                    "enrollments_created_count": int(enr_created_cnt),
                    "enrollmentsActiveCount": int(enr_active_cnt),
                    "enrollments_active_count": int(enr_active_cnt),
                    "conversionRate": round(rate, 2),
                    "conversion_rate": round(rate, 2),
                })
                cur += timedelta(days=1)
        else:
            months = self._get_months_in_range(date_from, date_to)
            for yr, mo in months:
                start_dt, end_dt = self._get_date_range(yr, mo)

                vis_stmt = select(func.count(VisitorEnrollmentRequest.id)).where(
                    and_(
                        VisitorEnrollmentRequest.created_at >= start_dt,
                        VisitorEnrollmentRequest.created_at < end_dt,
                    )
                )
                vis_cnt = (await self.session.execute(vis_stmt)).scalar() or 0

                vis_conv_stmt = select(func.count(VisitorEnrollmentRequest.id)).where(
                    and_(
                        VisitorEnrollmentRequest.created_at >= start_dt,
                        VisitorEnrollmentRequest.created_at < end_dt,
                        VisitorEnrollmentRequest.status == "converted",
                    )
                )
                vis_conv_cnt = (await self.session.execute(vis_conv_stmt)).scalar() or 0

                enr_created_stmt = select(func.count(Enrollment.id)).where(
                    and_(
                        Enrollment.created_at >= start_dt,
                        Enrollment.created_at < end_dt,
                    )
                )
                if branch_id is not None:
                    enr_created_stmt = enr_created_stmt.where(Enrollment.branch_id == branch_id)
                enr_created_cnt = (await self.session.execute(enr_created_stmt)).scalar() or 0

                enr_active_stmt = select(func.count(Enrollment.id)).where(
                    and_(
                        Enrollment.status == "active",
                        or_(
                            and_(Enrollment.activated_at >= start_dt, Enrollment.activated_at < end_dt),
                            and_(Enrollment.created_at >= start_dt, Enrollment.created_at < end_dt),
                        )
                    )
                )
                if branch_id is not None:
                    enr_active_stmt = enr_active_stmt.where(Enrollment.branch_id == branch_id)
                enr_active_cnt = (await self.session.execute(enr_active_stmt)).scalar() or 0

                rate = float((vis_conv_cnt / vis_cnt) * 100) if vis_cnt > 0 else 0.0

                start_d = date(yr, mo, 1)
                is_final_flag = check_is_final(start_d, "month")
                label_str = format_analytics_label(yr, mo, None, "month", locale)

                points.append({
                    "granularity": "month",
                    "day": None,
                    "isFinal": is_final_flag,
                    "is_final": is_final_flag,
                    "label": label_str,
                    "year": yr,
                    "month": mo,
                    "visitorRequestsCount": int(vis_cnt),
                    "visitor_requests_count": int(vis_cnt),
                    "visitorRequestsConvertedCount": int(vis_conv_cnt),
                    "visitor_requests_converted_count": int(vis_conv_cnt),
                    "enrollmentsCreatedCount": int(enr_created_cnt),
                    "enrollments_created_count": int(enr_created_cnt),
                    "enrollmentsActiveCount": int(enr_active_cnt),
                    "enrollments_active_count": int(enr_active_cnt),
                    "conversionRate": round(rate, 2),
                    "conversion_rate": round(rate, 2),
                })

        return points

    async def get_operations_trend(
        self,
        date_from: date,
        date_to: date,
        branch_id: Optional[int] = None,
        locale: str = "ar",
    ) -> List[Dict[str, Any]]:
        days_inclusive = (date_to - date_from).days + 1
        points: List[Dict[str, Any]] = []

        if days_inclusive <= 31:
            cur = date_from
            today_d = date.today()
            while cur <= date_to:
                abs_stmt = select(func.count(ClassSession.id)).where(
                    and_(
                        ClassSession.session_date == cur,
                        ClassSession.status == "teacher_absent",
                    )
                )
                if branch_id is not None:
                    abs_stmt = abs_stmt.where(ClassSession.branch_id == branch_id)
                abs_cnt = (await self.session.execute(abs_stmt)).scalar() or 0

                resched_stmt = select(func.count(ClassSession.id)).where(
                    and_(
                        ClassSession.session_date == cur,
                        or_(
                            ClassSession.status == "rescheduled",
                            ClassSession.original_session_id.isnot(None),
                        ),
                    )
                )
                if branch_id is not None:
                    resched_stmt = resched_stmt.where(ClassSession.branch_id == branch_id)
                resched_cnt = (await self.session.execute(resched_stmt)).scalar() or 0

                is_final_flag = cur < today_d
                label_str = format_analytics_label(cur.year, cur.month, cur.day, "day", locale)

                points.append({
                    "granularity": "day",
                    "day": cur.day,
                    "isFinal": is_final_flag,
                    "is_final": is_final_flag,
                    "label": label_str,
                    "year": cur.year,
                    "month": cur.month,
                    "teacherAbsencesCount": int(abs_cnt),
                    "teacher_absences_count": int(abs_cnt),
                    "reschedulesApprovedCount": int(resched_cnt),
                    "reschedules_approved_count": int(resched_cnt),
                })
                cur += timedelta(days=1)
        else:
            months = self._get_months_in_range(date_from, date_to)
            for yr, mo in months:
                start_d = date(yr, mo, 1)
                if mo == 12:
                    end_d = date(yr + 1, 1, 1) - timedelta(days=1)
                else:
                    end_d = date(yr, mo + 1, 1) - timedelta(days=1)

                abs_stmt = select(func.count(ClassSession.id)).where(
                    and_(
                        ClassSession.session_date >= start_d,
                        ClassSession.session_date <= end_d,
                        ClassSession.status == "teacher_absent",
                    )
                )
                if branch_id is not None:
                    abs_stmt = abs_stmt.where(ClassSession.branch_id == branch_id)
                abs_cnt = (await self.session.execute(abs_stmt)).scalar() or 0

                resched_stmt = select(func.count(ClassSession.id)).where(
                    and_(
                        ClassSession.session_date >= start_d,
                        ClassSession.session_date <= end_d,
                        or_(
                            ClassSession.status == "rescheduled",
                            ClassSession.original_session_id.isnot(None),
                        ),
                    )
                )
                if branch_id is not None:
                    resched_stmt = resched_stmt.where(ClassSession.branch_id == branch_id)
                resched_cnt = (await self.session.execute(resched_stmt)).scalar() or 0

                is_final_flag = check_is_final(start_d, "month")
                label_str = format_analytics_label(yr, mo, None, "month", locale)

                points.append({
                    "granularity": "month",
                    "day": None,
                    "isFinal": is_final_flag,
                    "is_final": is_final_flag,
                    "label": label_str,
                    "year": yr,
                    "month": mo,
                    "teacherAbsencesCount": int(abs_cnt),
                    "teacher_absences_count": int(abs_cnt),
                    "reschedulesApprovedCount": int(resched_cnt),
                    "reschedules_approved_count": int(resched_cnt),
                })

        return points

    # ─── Additional Analytics Methods ─────────────────────────────────────────

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
