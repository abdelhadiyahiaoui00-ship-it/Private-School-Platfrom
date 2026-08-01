"""
Enrollment Engine — shared logic for capacity decision and FIFO promotion.
Used by both visitor-enrollment and authenticated enrollment paths.
"""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.enrollments.models import Enrollment
from src.modules.groups.models import Group


async def decide_enrollment_status(
    db: AsyncSession,
    group: Group,
) -> tuple[str, Optional[int]]:
    """
    Capacity check with row-level lock on the group to prevent race conditions.
    Returns (status, waitlist_position).
    """
    # Row-level lock on the group row — prevents two simultaneous requests
    # both seeing "1 seat left" and both receiving "pending"
    await db.execute(
        select(Group).where(Group.id == group.id).with_for_update()
    )

    from src.modules.enrollments.repository import EnrollmentRepository
    repo = EnrollmentRepository(db)
    active_count = await repo.count_active_enrollments(group.id)

    if active_count < group.max_students:
        return "pending", None

    last_position = await repo.get_max_waitlist_position(group.id)
    return "waitlisted", last_position + 1


async def promote_next_in_waitlist(
    db: AsyncSession,
    group_id: int,
    actor_user_id: Optional[int] = None,
    is_manual: bool = False,
) -> Optional[Enrollment]:
    """
    FIFO promotion — single shared function invoked from every cancellation path.
    1. Lock the group row.
    2. Re-check capacity.
    3. If seat open: promote the lowest-position waitlisted enrollment.
    4. Re-sequence remaining waitlist positions.
    5. Insert enrollment_promoted notification.
    6. Return the promoted enrollment (or None if waitlist empty).
    """
    from src.modules.enrollments.repository import EnrollmentRepository

    # Lock group row
    await db.execute(
        select(Group).where(Group.id == group_id).with_for_update()
    )

    repo = EnrollmentRepository(db)
    active_count = await repo.count_active_enrollments(group_id)

    group_result = await db.execute(select(Group).where(Group.id == group_id))
    group = group_result.scalar_one_or_none()
    if not group or active_count >= group.max_students:
        return None  # No seat to promote into

    next_enrollment = await repo.get_next_in_waitlist(group_id)
    if not next_enrollment:
        return None

    next_enrollment.status = "pending"
    next_enrollment.waitlist_position = None
    await db.flush()

    # Re-sequence remaining waitlist
    await repo.resequence_waitlist(group_id)

    # Insert notification
    if next_enrollment.student_id:
        from src.modules.notifications.service import create_notification
        await create_notification(
            db,
            user_id=next_enrollment.student_id,
            type="enrollment_promoted",
            title="تمت ترقيتك من قائمة الانتظار",
            message="أصبح لديك مقعد متاح. يرجى زيارة الفرع لإتمام الدفع.",
            entity_type="enrollment",
            entity_id=next_enrollment.id,
        )

    from src.modules.audit.service import log_action
    await log_action(
        db,
        user_id=actor_user_id,
        action="ENROLLMENT_PROMOTED",
        category="enrollments",
        entity_type="enrollment",
        entity_id=next_enrollment.id,
        metadata={"groupId": group_id, "manual": is_manual},
    )

    return next_enrollment
