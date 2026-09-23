"""
Scheduled notification sweeps — Sprint 11.

Executes three independent sweeps:
1) subscription_expiring (monthly & session-based)
2) subscription_expired (monthly & session-based)
3) assignment_due_soon (active enrollments, missing submission)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.config import settings
from src.modules.config.models import SystemConfig
from src.modules.subscriptions.models import Subscription
from src.modules.assignments.models import Assignment, AssignmentSubmission
from src.modules.enrollments.models import Enrollment
from src.modules.notifications.models import Notification
from src.modules.notifications.service import create_notification, send_email_notification
from src.modules.users.models import User, ParentStudentLink
from src.common.notification_deep_link import resolve_notification_route

logger = logging.getLogger(settings.APP_NAME)


async def run_notification_sweeps(db: AsyncSession) -> dict[str, int]:
    """
    Run all three scheduled notification sweeps.
    Returns a dictionary with match counts for each sweep.
    """
    results = {
        "subscription_expiring": 0,
        "subscription_expired": 0,
        "assignment_due_soon": 0,
    }

    # Load system_config thresholds
    config_res = await db.execute(select(SystemConfig).limit(1))
    config = config_res.scalar_one_or_none()

    monthly_warning_days = getattr(config, "monthly_expiry_warning_days", 3) if config else 3
    session_warning_sessions = getattr(config, "session_based_expiry_warning_sessions", 3) if config else 3
    due_warning_hours = getattr(config, "assignment_due_soon_warning_hours", 24) if config else 24
    school_name = getattr(config, "school_name", "Académie Al-Nour") if config else "Académie Al-Nour"

    now = datetime.now(timezone.utc)
    today = now.date()

    # Helper: get linked parent user IDs for a student
    async def get_parent_ids(student_id: int) -> list[int]:
        parent_res = await db.execute(
            select(ParentStudentLink.parent_id).where(ParentStudentLink.student_id == student_id)
        )
        return list(parent_res.scalars().all())

    # Helper: load target users by ID list
    async def load_users(user_ids: list[int]) -> list[User]:
        if not user_ids:
            return []
        users_res = await db.execute(select(User).where(User.id.in_(user_ids)))
        return list(users_res.scalars().all())

    # ── Sweep 1: subscription_expiring ───────────────────────────────────────
    try:
        threshold_date = today + timedelta(days=monthly_warning_days)
        expiring_stmt = (
            select(Subscription)
            .options(
                selectinload(Subscription.group),
            )
            .where(
                and_(
                    Subscription.status == "active",
                    or_(
                        and_(
                            Subscription.type == "monthly",
                            Subscription.end_date != None,  # noqa: E711
                            Subscription.end_date <= threshold_date,
                            Subscription.end_date >= today,
                        ),
                        and_(
                            Subscription.type == "session_based",
                            Subscription.remaining_sessions != None,  # noqa: E711
                            Subscription.remaining_sessions <= session_warning_sessions,
                            Subscription.remaining_sessions > 0,
                        ),
                    ),
                )
            )
        )
        expiring_res = await db.execute(expiring_stmt)
        expiring_subs = expiring_res.scalars().all()

        twenty_four_hours_ago = now - timedelta(hours=24)

        for sub in expiring_subs:
            if not sub.student_id:
                continue

            # Dedup guard: check if subscription_expiring notification for this subscription exists in last 24h
            recent_check = await db.execute(
                select(Notification.id).where(
                    and_(
                        Notification.entity_type == "subscription",
                        Notification.entity_id == sub.id,
                        Notification.type == "subscription_expiring",
                        Notification.created_at >= twenty_four_hours_ago,
                    )
                ).limit(1)
            )
            if recent_check.scalar_one_or_none():
                continue  # Skip if already notified in last 24h

            parent_ids = await get_parent_ids(sub.student_id)
            target_ids = list(set([sub.student_id] + parent_ids))
            target_users = await load_users(target_ids)

            class_name = ""
            if sub.group:
                if getattr(sub.group, "class_", None):
                    class_name = sub.group.class_.name
                else:
                    class_name = sub.group.name

            expiry_str = str(sub.end_date) if sub.end_date else "N/A"
            remaining = sub.remaining_sessions

            for user in target_users:
                link = resolve_notification_route("subscription_expiring", "subscription", sub.id, user) or "/dashboard/my-subscriptions"
                first_name = user.first_name or ""
                last_name = user.last_name or ""
                full_name = f"{first_name} {last_name}".strip()

                await create_notification(
                    db,
                    user_id=user.id,
                    type="subscription_expiring",
                    title="اشتراكك ينتهي قريباً",
                    message=f"اشتراكك في {class_name} ينتهي قريباً",
                    entity_type="subscription",
                    entity_id=sub.id,
                    link=link,
                    recipient_user=user,
                )
                await send_email_notification(
                    db,
                    user_id=user.id,
                    notification_type="subscription_expiring",
                    template_vars={
                        "schoolName": school_name,
                        "firstName": first_name,
                        "lastName": last_name,
                        "fullName": full_name,
                        "className": class_name,
                        "expiryDate": expiry_str,
                        "remainingSessions": remaining,
                        "dashboardLink": link,
                    },
                )
            results["subscription_expiring"] += 1
    except Exception as exc:
        logger.error("Sweep 1 (subscription_expiring) failed: %s", exc, exc_info=True)

    # ── Sweep 2: subscription_expired ────────────────────────────────────────
    try:
        expired_stmt = (
            select(Subscription)
            .options(
                selectinload(Subscription.group),
            )
            .where(
                and_(
                    Subscription.status == "active",
                    or_(
                        and_(
                            Subscription.type == "monthly",
                            Subscription.end_date != None,  # noqa: E711
                            Subscription.end_date < today,
                        ),
                        and_(
                            Subscription.type == "session_based",
                            Subscription.remaining_sessions != None,  # noqa: E711
                            Subscription.remaining_sessions <= 0,
                        ),
                    ),
                )
            )
        )
        expired_res = await db.execute(expired_stmt)
        expired_subs = expired_res.scalars().all()

        for sub in expired_subs:
            # Mark subscription as expired
            sub.status = "expired"

            if not sub.student_id:
                continue

            # Dedup guard: check if subscription_expired notification already exists for this entity_id
            exist_check = await db.execute(
                select(Notification.id).where(
                    and_(
                        Notification.entity_type == "subscription",
                        Notification.entity_id == sub.id,
                        Notification.type == "subscription_expired",
                    )
                ).limit(1)
            )
            if exist_check.scalar_one_or_none():
                continue  # Already notified permanently

            parent_ids = await get_parent_ids(sub.student_id)
            target_ids = list(set([sub.student_id] + parent_ids))
            target_users = await load_users(target_ids)

            class_name = ""
            if sub.group:
                if getattr(sub.group, "class_", None):
                    class_name = sub.group.class_.name
                else:
                    class_name = sub.group.name

            expiry_str = str(sub.end_date) if sub.end_date else "N/A"

            for user in target_users:
                link = resolve_notification_route("subscription_expired", "subscription", sub.id, user) or "/dashboard/my-subscriptions"
                first_name = user.first_name or ""
                last_name = user.last_name or ""
                full_name = f"{first_name} {last_name}".strip()

                await create_notification(
                    db,
                    user_id=user.id,
                    type="subscription_expired",
                    title="انتهى اشتراكك",
                    message=f"انتهى اشتراكك في {class_name} بتاريخ {expiry_str}",
                    entity_type="subscription",
                    entity_id=sub.id,
                    link=link,
                    recipient_user=user,
                )
                await send_email_notification(
                    db,
                    user_id=user.id,
                    notification_type="subscription_expired",
                    template_vars={
                        "schoolName": school_name,
                        "firstName": first_name,
                        "lastName": last_name,
                        "fullName": full_name,
                        "className": class_name,
                        "expiryDate": expiry_str,
                        "dashboardLink": link,
                    },
                )
            results["subscription_expired"] += 1
    except Exception as exc:
        logger.error("Sweep 2 (subscription_expired) failed: %s", exc, exc_info=True)

    # ── Sweep 3: assignment_due_soon ──────────────────────────────────────────
    try:
        due_window_end = now + timedelta(hours=due_warning_hours)
        assignments_stmt = (
            select(Assignment, Enrollment.student_id)
            .join(Enrollment, and_(Enrollment.group_id == Assignment.group_id, Enrollment.status == "active"))
            .options(
                selectinload(Assignment.group),
                selectinload(Assignment.class_),
            )
            .where(
                and_(
                    Assignment.due_date != None,  # noqa: E711
                    Assignment.due_date > now,
                    Assignment.due_date <= due_window_end,
                )
            )
        )
        assignments_res = await db.execute(assignments_stmt)
        assignment_pairs = assignments_res.all()

        for assignment, student_id in assignment_pairs:
            # Check if student has already submitted
            sub_check = await db.execute(
                select(AssignmentSubmission.id).where(
                    and_(
                        AssignmentSubmission.assignment_id == assignment.id,
                        AssignmentSubmission.student_id == student_id,
                    )
                ).limit(1)
            )
            if sub_check.scalar_one_or_none():
                continue  # Already submitted

            parent_ids = await get_parent_ids(student_id)
            target_ids = list(set([student_id] + parent_ids))
            target_users = await load_users(target_ids)

            class_name = ""
            if assignment.class_:
                class_name = assignment.class_.name
            elif assignment.group:
                class_name = getattr(assignment.group.class_, "name", assignment.group.name)

            due_date_str = assignment.due_date.strftime("%Y-%m-%d %H:%M") if assignment.due_date else "N/A"
            sent_any = False

            for user in target_users:
                # Dedup guard per (assignment_id, user_id)
                notif_check = await db.execute(
                    select(Notification.id).where(
                        and_(
                            Notification.entity_type == "assignment",
                            Notification.entity_id == assignment.id,
                            Notification.user_id == user.id,
                            Notification.type == "assignment_due_soon",
                        )
                    ).limit(1)
                )
                if notif_check.scalar_one_or_none():
                    continue  # Already sent to this user

                link = resolve_notification_route("assignment_due_soon", "assignment", assignment.id, user) or "/dashboard/my-assignments"
                first_name = user.first_name or ""
                last_name = user.last_name or ""
                full_name = f"{first_name} {last_name}".strip()

                await create_notification(
                    db,
                    user_id=user.id,
                    type="assignment_due_soon",
                    title="تذكير: اقتراب موعد تسليم الواجب",
                    message=f"الواجب '{assignment.title}' في {class_name} يستحق في {due_date_str}",
                    entity_type="assignment",
                    entity_id=assignment.id,
                    link=link,
                    recipient_user=user,
                )
                await send_email_notification(
                    db,
                    user_id=user.id,
                    notification_type="assignment_due_soon",
                    template_vars={
                        "schoolName": school_name,
                        "firstName": first_name,
                        "lastName": last_name,
                        "fullName": full_name,
                        "assignmentTitle": assignment.title,
                        "className": class_name,
                        "dueDate": due_date_str,
                        "dashboardLink": link,
                    },
                )
                sent_any = True

            if sent_any:
                results["assignment_due_soon"] += 1

    except Exception as exc:
        logger.error("Sweep 3 (assignment_due_soon) failed: %s", exc, exc_info=True)

    await db.commit()
    logger.info("run_notification_sweeps complete: %s", results)
    return results
