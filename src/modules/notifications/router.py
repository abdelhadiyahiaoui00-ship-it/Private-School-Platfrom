from fastapi import APIRouter, Query
from src.core.database import DBSessionDep
from src.modules.auth.dependencies import CurrentUser
from src.modules.notifications.repository import NotificationRepository
from src.modules.notifications.schemas import NotificationResponse
from src.common.pagination import build_pagination

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", summary="Get notifications for current user")
async def get_notifications(
    actor: CurrentUser,
    session: DBSessionDep,
    unread: bool = Query(False),
    limit: int = Query(20, ge=1, le=100),
    page: int = Query(1, ge=1),
):
    repo = NotificationRepository(session)
    items, total, unread_count = await repo.get_for_user(
        user_id=actor.id,
        unread_only=unread,
        limit=limit,
        page=page,
    )
    pagination = build_pagination(page, limit, total)
    return {
        "data": {
            "items": [NotificationResponse.model_validate(n).model_dump(by_alias=True) for n in items],
            "unreadCount": unread_count,
            "pagination": pagination,
        }
    }


# IMPORTANT: read-all MUST be registered before /{notification_id}/read
@router.patch("/read-all", summary="Mark all notifications as read")
async def mark_all_read(
    actor: CurrentUser,
    session: DBSessionDep,
):
    repo = NotificationRepository(session)
    count = await repo.mark_all_read(actor.id)
    return {"data": {"markedRead": count}}


@router.patch("/{notification_id}/read", summary="Mark notification as read")
async def mark_read(
    notification_id: int,
    actor: CurrentUser,
    session: DBSessionDep,
):
    repo = NotificationRepository(session)
    await repo.mark_read(notification_id, actor.id)
    return {"data": {"read": True}}
