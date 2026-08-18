from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.audit.service import log_action
from src.modules.attendance.exceptions import (
    AttendanceSessionNotMarkable,
    CannotMarkPresentSubscriptionExpired,
)
from src.modules.attendance.models import Attendance
from src.modules.attendance.schemas import (
    AttendanceMatrixResponse,
    AttendanceRecordIn,
    AttendanceRecordResponse,
    AttendanceRosterResponse,
    AttendanceSummary,
    MatrixCell,
    MatrixSessionColumn,
    MatrixStudentRow,
    RosterEntry,
    SubscriptionBalanceSummary,
)
from src.modules.enrollments.models import Enrollment
from src.modules.enrollments.schemas import StudentBasic
from src.modules.sessions.models import Session
from src.modules.subscriptions.models import Subscription
from src.modules.users.models import User


ATTENDANCE_STATUSES = {"present", "absent", "excused"}


def _is_authorized_for_override(actor: User) -> bool:
    if actor.role in ("owner", "superAdmin"):
        return True
    if actor.role == "admin":
        perms = actor.permissions or {}
        return bool(perms.get("manageSessions"))
    return False


async def _resolve_any_subscription(
    db: AsyncSession, student_id: int, group_id: int
) -> Optional[Subscription]:
    result = await db.execute(
        select(Subscription)
        .where(
            Subscription.student_id == student_id,
            Subscription.group_id == group_id,
            Subscription.status == "active",
        )
        .order_by(Subscription.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _resolve_session_based_subscription(
    db: AsyncSession, student_id: int, group_id: int
) -> Optional[Subscription]:
    result = await db.execute(
        select(Subscription)
        .where(
            Subscription.student_id == student_id,
            Subscription.group_id == group_id,
            Subscription.type == "session_based",
            Subscription.status == "active",
        )
        .order_by(Subscription.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _resolve_latest_active_subscription_map(
    db: AsyncSession,
    student_ids: set[int],
    group_id: int,
    type_: Optional[str] = None,
) -> dict[int, Subscription]:
    if not student_ids:
        return {}

    query = select(Subscription).where(
        Subscription.student_id.in_(student_ids),
        Subscription.group_id == group_id,
        Subscription.status == "active",
    )
    if type_:
        query = query.where(Subscription.type == type_)
    query = query.order_by(
        Subscription.student_id.asc(),
        Subscription.created_at.desc(),
        Subscription.id.desc(),
    )

    result = await db.execute(query)
    subscriptions: dict[int, Subscription] = {}
    for sub in result.scalars().all():
        if sub.student_id not in subscriptions:
            subscriptions[sub.student_id] = sub
    return subscriptions


def _subscription_is_expired(sub: Optional[Subscription]) -> bool:
    if sub is None:
        return True
    if sub.type == "monthly":
        return sub.end_date is not None and sub.end_date < date.today()
    return sub.remaining_sessions is None or sub.remaining_sessions <= 0


def _build_subscription_summary(
    sub: Optional[Subscription],
    monthly_warning_days: int = 3,
    session_warning_count: int = 3,
) -> SubscriptionBalanceSummary:
    if sub is None:
        return SubscriptionBalanceSummary(
            has_active_subscription=False,
            type=None,
            remaining_sessions=None,
            total_sessions=None,
            end_date=None,
            is_expiring_soon=False,
            is_expired=True,
        )

    today = date.today()
    is_expired = _subscription_is_expired(sub)
    is_expiring_soon = False
    if sub.type == "monthly" and sub.end_date and not is_expired:
        is_expiring_soon = sub.end_date <= today + timedelta(days=monthly_warning_days)
    elif sub.type == "session_based" and sub.remaining_sessions is not None:
        is_expiring_soon = (not is_expired) and sub.remaining_sessions <= session_warning_count

    return SubscriptionBalanceSummary(
        has_active_subscription=True,
        type=sub.type,
        remaining_sessions=sub.remaining_sessions,
        total_sessions=sub.total_sessions,
        end_date=sub.end_date,
        is_expiring_soon=is_expiring_soon,
        is_expired=is_expired,
    )


async def _get_expiry_warning_config(db: AsyncSession) -> tuple[int, int]:
    from src.modules.config.models import SystemConfig

    config_result = await db.execute(select(SystemConfig).limit(1))
    config = config_result.scalar_one_or_none()
    if not config:
        return 3, 3
    return (
        config.monthly_expiry_warning_days,
        config.session_based_expiry_warning_sessions,
    )


async def _build_roster(
    db: AsyncSession, session: Session, actor: User
) -> tuple[list[RosterEntry], bool]:
    today = date.today()
    can_mark = session.status in ("scheduled", "completed") and session.session_date <= today

    active_result = await db.execute(
        select(Enrollment).where(
            Enrollment.group_id == session.group_id,
            Enrollment.status == "active",
            Enrollment.student_id.isnot(None),
        )
    )
    active_enrollments = active_result.scalars().all()
    active_student_ids = {e.student_id for e in active_enrollments}

    historical_result = await db.execute(
        select(Attendance.student_id)
        .where(Attendance.session_id == session.id)
        .distinct()
    )
    historical_student_ids = {row[0] for row in historical_result.all()}
    all_student_ids = active_student_ids | historical_student_ids

    if not all_student_ids:
        return [], can_mark

    att_result = await db.execute(
        select(Attendance)
        .where(
            Attendance.session_id == session.id,
            Attendance.student_id.in_(all_student_ids),
        )
        .options(selectinload(Attendance.marker))
    )
    att_map = {a.student_id: a for a in att_result.scalars().all()}

    from src.modules.users.models import User as UserModel

    users_result = await db.execute(
        select(UserModel).where(UserModel.id.in_(all_student_ids))
    )
    users_map = {u.id: u for u in users_result.scalars().all()}

    monthly_warning, session_warning = await _get_expiry_warning_config(db)
    admin_override_allowed = _is_authorized_for_override(actor)
    sub_map = await _resolve_latest_active_subscription_map(
        db, all_student_ids, session.group_id
    )

    entries: list[RosterEntry] = []
    for student_id in sorted(all_student_ids):
        user = users_map.get(student_id)
        if not user:
            continue

        student = StudentBasic(
            id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            avatar_url=user.avatar_url,
            date_of_birth=user.date_of_birth,
        )
        sub = sub_map.get(student_id)
        is_expired = _subscription_is_expired(sub)
        can_mark_present = not is_expired or admin_override_allowed

        att = att_map.get(student_id)
        attendance = None
        if att:
            marker_name = None
            if att.marker:
                marker_name = f"{att.marker.first_name} {att.marker.last_name}"
            attendance = AttendanceRecordResponse(
                student_id=student_id,
                status=att.status,
                session_consumed=att.session_consumed,
                is_override=att.is_override,
                marked_at=att.marked_at,
                marked_by_name=marker_name,
            )

        entries.append(
            RosterEntry(
                student=student,
                is_currently_enrolled=student_id in active_student_ids,
                subscription=_build_subscription_summary(
                    sub, monthly_warning, session_warning
                ),
                attendance=attendance,
                can_mark_present=can_mark_present,
            )
        )

    return entries, can_mark


class AttendanceService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _get_session_or_404(self, session_id: int) -> Session:
        result = await self._session.execute(select(Session).where(Session.id == session_id))
        session = result.scalar_one_or_none()
        if not session:
            from src.core.exceptions import ResourceNotFound

            raise ResourceNotFound(message="Session not found.")
        return session

    async def get_roster(self, session_id: int, actor: User) -> dict:
        session = await self._get_session_or_404(session_id)
        await self._assert_session_access(session, actor)

        roster, can_mark = await _build_roster(self._session, session, actor)
        summary = AttendanceSummary(
            present_count=sum(
                1 for entry in roster if entry.attendance and entry.attendance.status == "present"
            ),
            absent_count=sum(
                1 for entry in roster if entry.attendance and entry.attendance.status == "absent"
            ),
            excused_count=sum(
                1 for entry in roster if entry.attendance and entry.attendance.status == "excused"
            ),
            unmarked_count=sum(1 for entry in roster if not entry.attendance),
            total=len(roster),
        )

        return AttendanceRosterResponse(
            session=await self._build_session_detail_dict(session),
            can_mark_attendance=can_mark,
            roster=roster,
            summary=summary,
        ).model_dump(by_alias=True)

    async def save_attendance(
        self,
        session_id: int,
        records: list[AttendanceRecordIn],
        actor: User,
        ip: Optional[str] = None,
    ) -> dict:
        session = await self._get_session_or_404(session_id)
        await self._assert_session_access(session, actor)

        today = date.today()
        if session.status not in ("scheduled", "completed") or session.session_date > today:
            raise AttendanceSessionNotMarkable()

        for rec in records:
            if rec.status is not None and rec.status not in ATTENDANCE_STATUSES:
                from src.core.exceptions import ValidationError

                raise ValidationError(message="Invalid attendance status.")

        is_admin_override_allowed = _is_authorized_for_override(actor)
        student_ids = {rec.student_id for rec in records}
        sub_map = await _resolve_latest_active_subscription_map(
            self._session, student_ids, session.group_id
        )
        session_sub_map = await _resolve_latest_active_subscription_map(
            self._session, student_ids, session.group_id, type_="session_based"
        )

        violations: list[dict] = []
        violation_student_ids: set[int] = set()
        for rec in records:
            if rec.status != "present":
                continue
            sub = sub_map.get(rec.student_id)
            is_blocked = _subscription_is_expired(sub)
            is_override = rec.override_present is True and is_admin_override_allowed
            if is_blocked and not is_override:
                violation_student_ids.add(rec.student_id)

        if violation_student_ids:
            from src.modules.users.models import User as UserModel

            user_result = await self._session.execute(
                select(UserModel).where(UserModel.id.in_(violation_student_ids))
            )
            users_by_id = {user.id: user for user in user_result.scalars().all()}
            for student_id in sorted(violation_student_ids):
                user = users_by_id.get(student_id)
                student_name = f"{user.first_name} {user.last_name}" if user else str(student_id)
                violations.append(
                    {
                        "studentId": student_id,
                        "studentName": student_name,
                        "reason": "SUBSCRIPTION_EXPIRED",
                    }
                )

        if violations:
            raise CannotMarkPresentSubscriptionExpired(
                message="One or more students cannot be marked present - subscription expired or missing.",
                details=violations,
            )

        now = datetime.now(timezone.utc)
        first_mark = session.attendance_marked_at is None
        changed_records = 0
        override_count = 0
        existing_map: dict[int, Attendance] = {}
        if student_ids:
            existing_result = await self._session.execute(
                select(Attendance).where(
                    Attendance.session_id == session_id,
                    Attendance.student_id.in_(student_ids),
                )
            )
            existing_map = {
                attendance.student_id: attendance
                for attendance in existing_result.scalars().all()
            }

        for rec in records:
            existing = existing_map.get(rec.student_id)
            old_status = existing.status if existing else None
            old_consumed = existing.session_consumed if existing else False
            old_override = existing.is_override if existing else False

            if rec.status is None:
                if existing:
                    if old_status == "present" and old_consumed:
                        session_sub = session_sub_map.get(rec.student_id)
                        if session_sub:
                            locked_result = await self._session.execute(
                                select(Subscription)
                                .where(Subscription.id == session_sub.id)
                                .with_for_update()
                            )
                            locked_sub = locked_result.scalar_one_or_none()
                            if locked_sub:
                                locked_sub.remaining_sessions = (
                                    locked_sub.remaining_sessions or 0
                                ) + 1
                                session_sub_map[rec.student_id] = locked_sub
                                sub_map[rec.student_id] = locked_sub
                    await self._session.delete(existing)
                    changed_records += 1
                continue

            sub = sub_map.get(rec.student_id)
            session_sub = session_sub_map.get(rec.student_id)
            is_expired = _subscription_is_expired(sub)
            is_override = (
                rec.status == "present"
                and is_expired
                and rec.override_present
                and is_admin_override_allowed
            )

            session_consumed = old_consumed if old_status == rec.status else False
            if rec.status == "present":
                if old_status != "present":
                    if not is_override and sub and sub.type == "session_based":
                        locked_result = await self._session.execute(
                            select(Subscription)
                            .where(Subscription.id == sub.id)
                            .with_for_update()
                        )
                        locked_sub = locked_result.scalar_one_or_none()
                        if locked_sub:
                            locked_sub.remaining_sessions = max(
                                0, (locked_sub.remaining_sessions or 0) - 1
                            )
                            sub_map[rec.student_id] = locked_sub
                            session_sub_map[rec.student_id] = locked_sub
                        session_consumed = True
                    else:
                        session_consumed = False
                else:
                    is_override = old_override
            elif old_status == "present":
                if old_consumed and session_sub and session_sub.type == "session_based":
                    locked_result = await self._session.execute(
                        select(Subscription)
                        .where(Subscription.id == session_sub.id)
                        .with_for_update()
                    )
                    locked_sub = locked_result.scalar_one_or_none()
                    if locked_sub:
                        locked_sub.remaining_sessions = (
                            locked_sub.remaining_sessions or 0
                        ) + 1
                        session_sub_map[rec.student_id] = locked_sub
                        sub_map[rec.student_id] = locked_sub

            if existing:
                if (
                    existing.status != rec.status
                    or existing.session_consumed != session_consumed
                    or existing.is_override != is_override
                ):
                    changed_records += 1
                existing.status = rec.status
                existing.session_consumed = session_consumed
                existing.is_override = is_override
                existing.marked_at = now
                existing.marked_by = actor.id
            else:
                new_att = Attendance(
                    session_id=session_id,
                    student_id=rec.student_id,
                    status=rec.status,
                    session_consumed=session_consumed,
                    is_override=is_override,
                    marked_at=now,
                    marked_by=actor.id,
                )
                self._session.add(new_att)
                changed_records += 1

            if is_override:
                override_count += 1
                await log_action(
                    self._session,
                    user_id=actor.id,
                    action="ATTENDANCE_PRESENT_OVERRIDE",
                    category="sessions",
                    entity_type="attendance",
                    entity_id=rec.student_id,
                    metadata={
                        "studentId": rec.student_id,
                        "sessionId": session_id,
                        "reason": "subscription_expired",
                    },
                    ip_address=ip,
                )

        if session.status == "scheduled" and session.session_date <= today:
            session.status = "completed"

        session.attendance_marked_at = now
        session.attendance_marked_by = actor.id
        await self._session.flush()

        present_count = sum(1 for rec in records if rec.status == "present")
        absent_count = sum(1 for rec in records if rec.status == "absent")
        excused_count = sum(1 for rec in records if rec.status == "excused")

        if first_mark:
            await log_action(
                self._session,
                user_id=actor.id,
                action="ATTENDANCE_MARKED",
                category="sessions",
                entity_type="session",
                entity_id=session_id,
                metadata={
                    "presentCount": present_count,
                    "absentCount": absent_count,
                    "excusedCount": excused_count,
                    "overrideCount": override_count,
                },
                ip_address=ip,
            )
        else:
            await log_action(
                self._session,
                user_id=actor.id,
                action="ATTENDANCE_UPDATED",
                category="sessions",
                entity_type="session",
                entity_id=session_id,
                metadata={"changedRecords": changed_records, "overrideCount": override_count},
                ip_address=ip,
            )

        return await self.get_roster(session_id, actor)

    async def get_attendance_matrix(
        self,
        group_id: int,
        actor: User,
        anchor_date: Optional[date] = None,
        direction: str = "current",
        page_size: int = 8,
    ) -> dict:
        from src.modules.branches.models import Branch
        from src.modules.classes.models import Class as SchoolClass
        from src.modules.groups.models import Group
        from src.modules.modules.models import Module
        from src.modules.users.models import User as UserModel

        group_result = await self._session.execute(select(Group).where(Group.id == group_id))
        group = group_result.scalar_one_or_none()
        if not group:
            from src.core.exceptions import ResourceNotFound

            raise ResourceNotFound(message="Group not found.")

        await self._assert_group_access(group, actor)

        class_result = await self._session.execute(
            select(SchoolClass).where(SchoolClass.id == group.class_id)
        )
        cls = class_result.scalar_one_or_none()

        module = None
        if cls:
            module_result = await self._session.execute(
                select(Module).where(Module.id == cls.module_id)
            )
            module = module_result.scalar_one_or_none()

        branch = None
        if cls:
            branch_result = await self._session.execute(
                select(Branch).where(Branch.id == cls.branch_id)
            )
            branch = branch_result.scalar_one_or_none()

        teacher_id = group.teacher_id or (cls.teacher_id if cls else None)
        teacher_name = ""
        if teacher_id:
            teacher_result = await self._session.execute(
                select(UserModel).where(UserModel.id == teacher_id)
            )
            teacher = teacher_result.scalar_one_or_none()
            if teacher:
                teacher_name = f"{teacher.first_name} {teacher.last_name}"

        today = date.today()
        anchor = anchor_date or today

        all_sessions_result = await self._session.execute(
            select(Session)
            .where(Session.group_id == group_id)
            .order_by(Session.session_date.asc(), Session.start_time.asc())
        )
        all_sessions = all_sessions_result.scalars().all()

        if direction == "current":
            window = [session for session in all_sessions if session.session_date <= anchor]
            window = window[-page_size:]
        elif direction == "prev":
            window = [session for session in all_sessions if session.session_date < anchor]
            window = window[-page_size:]
        elif direction == "next":
            window = [session for session in all_sessions if session.session_date > anchor]
            window = window[:page_size]
        else:
            from src.core.exceptions import ValidationError

            raise ValidationError(message="Invalid direction.")

        min_date = min((session.session_date for session in window), default=today)
        max_date = max((session.session_date for session in window), default=today)
        has_prev = any(session.session_date < min_date for session in all_sessions)
        has_next = any(session.session_date > max_date for session in all_sessions)
        window_ids = [session.id for session in window]

        enrolled_result = await self._session.execute(
            select(Enrollment).where(
                Enrollment.group_id == group_id,
                Enrollment.status == "active",
                Enrollment.student_id.isnot(None),
            )
        )
        active_student_ids = {e.student_id for e in enrolled_result.scalars().all()}

        historical_ids: set[int] = set()
        if window_ids:
            historical_result = await self._session.execute(
                select(Attendance.student_id)
                .where(Attendance.session_id.in_(window_ids))
                .distinct()
            )
            historical_ids = {row[0] for row in historical_result.all()}
        all_student_ids = active_student_ids | historical_ids

        if not all_student_ids:
            return AttendanceMatrixResponse(
                group_id=group_id,
                group_name=group.name,
                class_name=cls.name if cls else "",
                module_name=module.name if module else "",
                teacher_name=teacher_name,
                branch_name=branch.name if branch else "",
                sessions=[],
                students=[],
                date_range_label=self._format_date_range(window),
                has_next_page=has_next,
                has_prev_page=has_prev,
            ).model_dump(by_alias=True)

        att_map: dict[tuple[int, int], Attendance] = {}
        if window_ids:
            att_result = await self._session.execute(
                select(Attendance).where(
                    Attendance.session_id.in_(window_ids),
                    Attendance.student_id.in_(all_student_ids),
                )
            )
            att_map = {
                (att.session_id, att.student_id): att
                for att in att_result.scalars().all()
            }

        users_result = await self._session.execute(
            select(UserModel).where(UserModel.id.in_(all_student_ids))
        )
        users_map = {user.id: user for user in users_result.scalars().all()}

        monthly_warning, session_warning = await _get_expiry_warning_config(self._session)
        admin_override_allowed = _is_authorized_for_override(actor)
        sub_map = await _resolve_latest_active_subscription_map(
            self._session, all_student_ids, group_id
        )
        students_out: list[MatrixStudentRow] = []
        for student_id in sorted(all_student_ids):
            user = users_map.get(student_id)
            if not user:
                continue

            student = StudentBasic(
                id=user.id,
                first_name=user.first_name,
                last_name=user.last_name,
                avatar_url=user.avatar_url,
                date_of_birth=user.date_of_birth,
            )
            sub = sub_map.get(student_id)
            is_expired = _subscription_is_expired(sub)
            can_mark_present = not is_expired or admin_override_allowed
            cells: list[MatrixCell] = []
            present_in_window = 0
            for sess in window:
                att = att_map.get((sess.id, student_id))
                cells.append(
                    MatrixCell(
                        session_id=sess.id,
                        status=att.status if att else None,
                        session_consumed=att.session_consumed if att else False,
                        is_override=att.is_override if att else False,
                    )
                )
                if att and att.status == "present":
                    present_in_window += 1

            students_out.append(
                MatrixStudentRow(
                    student=student,
                    is_currently_enrolled=student_id in active_student_ids,
                    subscription=_build_subscription_summary(
                        sub, monthly_warning, session_warning
                    ),
                    can_mark_present=can_mark_present,
                    cells=cells,
                    present_count_in_window=present_in_window,
                )
            )

        sessions_out = [
            MatrixSessionColumn(
                id=sess.id,
                session_date=sess.session_date,
                start_time=str(sess.start_time)[:5],
                end_time=str(sess.end_time)[:5],
                status=sess.status,
            )
            for sess in window
        ]

        return AttendanceMatrixResponse(
            group_id=group_id,
            group_name=group.name,
            class_name=cls.name if cls else "",
            module_name=module.name if module else "",
            teacher_name=teacher_name,
            branch_name=branch.name if branch else "",
            sessions=sessions_out,
            students=students_out,
            date_range_label=self._format_date_range(window),
            has_next_page=has_next,
            has_prev_page=has_prev,
        ).model_dump(by_alias=True)

    def _format_date_range(self, sessions: list[Session]) -> str:
        if not sessions:
            return ""
        dates = [session.session_date for session in sessions]
        return f"{min(dates).strftime('%Y-%m-%d')} - {max(dates).strftime('%Y-%m-%d')}"

    async def _assert_session_access(self, session: Session, actor: User) -> None:
        if actor.role in ("owner", "superAdmin"):
            return
        if actor.role == "admin":
            perms = actor.permissions or {}
            if perms.get("manageSessions") and self._actor_has_branch(actor, session.branch_id):
                return
        if actor.role == "teacher":
            from src.modules.classes.models import Class as SchoolClass
            from src.modules.groups.models import Group

            group_result = await self._session.execute(
                select(Group).where(Group.id == session.group_id)
            )
            group = group_result.scalar_one_or_none()
            if group:
                class_result = await self._session.execute(
                    select(SchoolClass).where(SchoolClass.id == group.class_id)
                )
                cls = class_result.scalar_one_or_none()
                effective_teacher = group.teacher_id or (cls.teacher_id if cls else None)
                if effective_teacher == actor.id:
                    return

        from src.core.exceptions import PermissionDenied

        raise PermissionDenied()

    async def _assert_group_access(self, group, actor: User) -> None:
        if actor.role in ("owner", "superAdmin"):
            return
        if actor.role == "admin":
            perms = actor.permissions or {}
            if perms.get("manageSessions"):
                from src.modules.classes.models import Class as SchoolClass

                class_result = await self._session.execute(
                    select(SchoolClass).where(SchoolClass.id == group.class_id)
                )
                cls = class_result.scalar_one_or_none()
                if cls and self._actor_has_branch(actor, cls.branch_id):
                    return
        if actor.role == "teacher":
            from src.modules.classes.models import Class as SchoolClass

            class_result = await self._session.execute(
                select(SchoolClass).where(SchoolClass.id == group.class_id)
            )
            cls = class_result.scalar_one_or_none()
            effective_teacher = group.teacher_id or (cls.teacher_id if cls else None)
            if effective_teacher == actor.id:
                return

        from src.core.exceptions import PermissionDenied

        raise PermissionDenied()

    def _actor_has_branch(self, actor: User, branch_id: int) -> bool:
        return any(link.branch_id == branch_id for link in (actor.branch_links or []))

    async def _build_session_detail_dict(self, session: Session) -> dict:
        return {
            "id": session.id,
            "groupId": session.group_id,
            "sessionDate": str(session.session_date),
            "startTime": str(session.start_time)[:5],
            "endTime": str(session.end_time)[:5],
            "room": session.room,
            "status": session.status,
            "attendanceMarkedAt": (
                session.attendance_marked_at.isoformat()
                if session.attendance_marked_at
                else None
            ),
        }
