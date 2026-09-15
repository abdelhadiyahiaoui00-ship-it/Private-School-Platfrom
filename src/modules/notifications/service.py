"""
Notification service — Sprint 11 update.

Functions:
  create_notification()       — create in-app notification (auto-populates link)
  mark_as_read()              — idempotent single-read
  mark_all_as_read()          — idempotent bulk-read, returns count
  send_email_notification()   — send email via EmailService (swallows errors)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update, and_
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
    # Pass the recipient User object so the deep-link resolver can be role-aware.
    # If omitted, no auto-link is generated (link must be supplied explicitly).
    recipient_user=None,
) -> None:
    """
    Create a notification row. Fails silently.

    If `link` is not provided, the deep-link resolver auto-generates one
    based on the recipient's role, entity_type, and entity_id.
    """
    try:
        # Auto-populate link if not explicitly provided
        if link is None and recipient_user is not None:
            from src.common.notification_deep_link import resolve_notification_route
            link = resolve_notification_route(type, entity_type, entity_id, recipient_user)

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


async def mark_as_read(
    session: AsyncSession,
    notification_id: int,
    user_id: int,
) -> bool:
    """
    Mark a single notification as read (idempotent).
    Returns True whether or not the row was already read.
    Returns False if the notification does not belong to user_id.
    """
    try:
        result = await session.execute(
            select(Notification).where(
                and_(
                    Notification.id == notification_id,
                    Notification.user_id == user_id,
                )
            )
        )
        notif = result.scalar_one_or_none()
        if notif is None:
            return False  # Not this user's notification
        if not notif.read_at:
            notif.is_read = True
            notif.read_at = datetime.now(timezone.utc)
            await session.commit()
        return True
    except Exception as exc:
        logger.error("mark_as_read error: %s", exc)
        return False


async def mark_all_as_read(
    session: AsyncSession,
    user_id: int,
) -> int:
    """
    Mark all unread notifications for user_id as read (idempotent).
    Returns the count of notifications that were updated (0 is valid).
    """
    try:
        result = await session.execute(
            update(Notification)
            .where(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_read == False,  # noqa: E712
                )
            )
            .values(is_read=True, read_at=datetime.now(timezone.utc))
        )
        count = result.rowcount
        if count > 0:
            await session.commit()
        return count
    except Exception as exc:
        logger.error("mark_all_as_read error: %s", exc)
        return 0


async def send_email_notification(
    session: AsyncSession,
    user_id: int,
    notification_type: str,
    template_vars: dict,
    locale: str = "ar",
) -> bool:
    """
    Send an email to user_id for the given notification type.

    Fetches the user's email address from the DB. Uses user.language
    as locale if not overridden by the caller. Swallows all errors.
    """
    from src.modules.users.models import User
    from src.infrastructure.mail.email_service import EmailService

    try:
        user_result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        if not user or not user.email:
            return False

        # Prefer user's stored language; caller-supplied locale is a fallback
        user_locale = getattr(user, "language", None)
        if user_locale not in ("ar", "en", "fr"):
            user_locale = locale
        if not user_locale:
            user_locale = "ar"

        email_service = EmailService()
        return await email_service.send_email(
            to=user.email,
            notification_type=notification_type,
            template_vars=template_vars,
            locale=user_locale,
        )
    except Exception as exc:
        logger.error("send_email_notification error type=%s user_id=%s: %s", notification_type, user_id, exc)
        return False
