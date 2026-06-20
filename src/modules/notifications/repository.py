from typing import Optional
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.notifications.models import Notification


class NotificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_for_user(
        self,
        user_id: int,
        unread_only: bool = False,
        limit: int = 20,
        page: int = 1,
    ) -> tuple[list[Notification], int, int]:
        q = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            q = q.where(Notification.is_read == False)
        q = q.order_by(Notification.created_at.desc())

        count_q = select(func.count()).select_from(
            select(Notification).where(Notification.user_id == user_id).subquery()
        )
        unread_q = select(func.count()).select_from(Notification).where(
            Notification.user_id == user_id, Notification.is_read == False
        )

        total = (await self._session.execute(count_q)).scalar_one()
        unread_count = (await self._session.execute(unread_q)).scalar_one()

        q = q.offset((page - 1) * limit).limit(limit)
        result = await self._session.execute(q)
        return list(result.scalars().all()), total, unread_count

    async def mark_read(self, notification_id: int, user_id: int) -> bool:
        from datetime import datetime, timezone
        result = await self._session.execute(
            update(Notification)
            .where(Notification.id == notification_id, Notification.user_id == user_id)
            .values(is_read=True, read_at=datetime.now(timezone.utc))
        )
        await self._session.flush()
        return result.rowcount > 0

    async def mark_all_read(self, user_id: int) -> int:
        from datetime import datetime, timezone
        result = await self._session.execute(
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read == False)
            .values(is_read=True, read_at=datetime.now(timezone.utc))
        )
        await self._session.flush()
        return result.rowcount
