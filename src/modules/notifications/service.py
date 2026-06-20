import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.modules.notifications.models import Notification

logger = logging.getLogger(settings.APP_NAME)


async def create_notification(
    session: AsyncSession,
    user_id: int,
    type: str,
    title: str,
    message: Optional[str] = None,
    link: Optional[str] = None,
    actor_id: Optional[int] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    metadata: Optional[dict] = None,
) -> None:
    """
    Create a notification. Fails silently.
    """
    try:
        notif = Notification(
            user_id=user_id,
            type=type,
            title=title,
            message=message,
            link=link,
            actor_id=actor_id,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata_=metadata,
        )
        session.add(notif)
    except Exception as exc:
        logger.error(f"Failed to append notification {type}: {exc}")
