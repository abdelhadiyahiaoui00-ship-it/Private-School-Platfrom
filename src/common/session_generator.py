"""
Session Generation Engine.
Generates Session rows for a group's schedule over a date range.
Idempotent: skips dates where a session already exists (group_id + session_date + start_time).
Respects class.period_end: stops generation at period_end if set and earlier than until_date.
"""
from datetime import date, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.modules.groups.models import Group
from src.modules.sessions.models import Session


async def generate_sessions(
    db: AsyncSession,
    group: Group,
    from_date: date,
    weeks_ahead: int,
    period_end: Optional[date] = None,
) -> tuple[list[Session], date]:
    """
    Generates sessions from from_date for weeks_ahead weeks.
    Returns (new_sessions, actual_until_date).
    actual_until_date may be earlier than computed if period_end truncates it.
    """
    computed_until = from_date + timedelta(weeks=weeks_ahead)

    # Respect class period_end
    if period_end and period_end < computed_until:
        actual_until = period_end
    else:
        actual_until = computed_until

    # Fetch existing sessions for this group in range to check idempotency
    existing = await db.execute(
        select(Session.session_date, Session.start_time)
        .where(
            Session.group_id == group.id,
            Session.session_date >= from_date,
            Session.session_date <= actual_until,
        )
    )
    existing_set = {(row.session_date, str(row.start_time)[:5]) for row in existing.all()}

    schedule = group.schedule or []
    new_sessions = []
    current = from_date

    while current <= actual_until:
        weekday = current.weekday()
        # Python weekday(): Mon=0, Tue=1, Wed=2, Thu=3, Fri=4, Sat=5, Sun=6
        # Schedule dayOfWeek: Sun=0, Mon=1, Tue=2, Wed=3, Thu=4, Fri=5, Sat=6
        schedule_day = (weekday + 1) % 7

        for slot in schedule:
            slot_day = slot.get("dayOfWeek")
            if slot_day != schedule_day:
                continue
            start_time_str = slot.get("startTime", "")[:5]
            if (current, start_time_str) in existing_set:
                continue
            existing_set.add((current, start_time_str))  # prevent double-add in same run

            # Resolve branch_id from group → class
            branch_id = None
            if hasattr(group, "class_") and group.class_ is not None:
                branch_id = group.class_.branch_id
            if branch_id is None:
                # Fallback: query class directly
                from src.modules.classes.models import Class
                from sqlalchemy import select as sa_select
                cls_result = await db.execute(
                    sa_select(Class).where(Class.id == group.class_id)
                )
                cls_obj = cls_result.scalar_one_or_none()
                branch_id = cls_obj.branch_id if cls_obj else 0

            s = Session(
                group_id=group.id,
                branch_id=branch_id,
                session_date=current,
                start_time=start_time_str,
                end_time=slot.get("endTime", "")[:5],
                room=group.room,
                status="scheduled",
            )
            db.add(s)
            new_sessions.append(s)

        current += timedelta(days=1)

    if new_sessions:
        await db.flush()

    return new_sessions, actual_until
