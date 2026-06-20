import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.modules.audit.models import ActivityLog

logger = logging.getLogger(settings.APP_NAME)


async def log_action(
    session: AsyncSession,
    user_id: Optional[int],
    action: str,
    category: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    metadata: Optional[dict] = None,
    ip_address: Optional[str] = None,
) -> None:
    """
    Log an action.
    Fails silently so it doesn't break business transactions.
    """
    try:
        log = ActivityLog(
            user_id=user_id,
            action=action,
            category=category,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata_=metadata,
            ip_address=ip_address,
        )
        session.add(log)
        # We don't flush here; the caller's commit will persist this
    except Exception as exc:
        logger.error(f"Failed to append activity log {action}: {exc}")
