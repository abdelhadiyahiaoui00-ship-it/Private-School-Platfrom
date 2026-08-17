"""
Reschedule Engine - Sprint 7.
The only implementation of "what rescheduling means".
"""
from datetime import date, time
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.notifications.service import create_notification
from src.modules.sessions.models import Session


async def apply_reschedule(
    db: AsyncSession,
    old_session: Session,
    new_date: date,
    new_start_time: time,
    new_end_time: time,
    new_room: Optional[str],
    actor_id: int,
) -> tuple[Session, Session]:
    old_session.status = "rescheduled"
    await db.flush()

    new_session = Session(
        group_id=old_session.group_id,
        branch_id=old_session.branch_id,
        session_date=new_date,
        start_time=new_start_time,
        end_time=new_end_time,
        room=new_room if new_room else old_session.room,
        status="scheduled",
        original_session_id=old_session.id,
    )
    db.add(new_session)
    await db.flush()
    await db.refresh(new_session)

    from src.modules.classes.models import Class as SchoolClass
    from src.modules.enrollments.models import Enrollment
    from src.modules.groups.models import Group
    from src.modules.users.models import ParentStudentLink

    enrolled_result = await db.execute(
        select(Enrollment).where(
            Enrollment.group_id == old_session.group_id,
            Enrollment.status == "active",
            Enrollment.student_id.isnot(None),
        )
    )
    enrollments = enrolled_result.scalars().all()

    notified_user_ids: set[int] = set()
    for enrollment in enrollments:
        student_id = enrollment.student_id
        if student_id and student_id not in notified_user_ids:
            notified_user_ids.add(student_id)
            await create_notification(
                db,
                user_id=student_id,
                type="session_rescheduled",
                title="تم تغيير موعد الحصة",
                message=f"تم تغيير موعد الحصة إلى {new_date} الساعة {str(new_start_time)[:5]}",
                entity_type="session",
                entity_id=new_session.id,
                actor_id=actor_id,
            )

            parents_result = await db.execute(
                select(ParentStudentLink.parent_id).where(
                    ParentStudentLink.student_id == student_id
                )
            )
            for (parent_id,) in parents_result.all():
                if parent_id not in notified_user_ids:
                    notified_user_ids.add(parent_id)
                    await create_notification(
                        db,
                        user_id=parent_id,
                        type="session_rescheduled",
                        title="تم تغيير موعد الحصة",
                        message=f"تم تغيير موعد حصة طفلك إلى {new_date} الساعة {str(new_start_time)[:5]}",
                        entity_type="session",
                        entity_id=new_session.id,
                        actor_id=actor_id,
                    )

    group_result = await db.execute(select(Group).where(Group.id == old_session.group_id))
    group = group_result.scalar_one_or_none()
    if group:
        class_result = await db.execute(select(SchoolClass).where(SchoolClass.id == group.class_id))
        cls = class_result.scalar_one_or_none()
        teacher_id = group.teacher_id or (cls.teacher_id if cls else None)
        if teacher_id and teacher_id not in notified_user_ids:
            await create_notification(
                db,
                user_id=teacher_id,
                type="session_rescheduled",
                title="تم تغيير موعد الحصة",
                message=f"تم تغيير موعد الحصة إلى {new_date} الساعة {str(new_start_time)[:5]}",
                entity_type="session",
                entity_id=new_session.id,
                actor_id=actor_id,
            )

    return old_session, new_session
