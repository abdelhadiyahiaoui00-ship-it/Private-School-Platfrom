from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request

from src.core.database import DBSessionDep
from src.modules.auth.dependencies import get_current_user, require_manage_sessions
from src.modules.sessions.schemas import (
    GenerateSessionsRequest, UpdateSessionRequest
)
from src.modules.sessions.service import SessionService
from src.modules.users.models import User

router = APIRouter(prefix="/sessions", tags=["Sessions"])


def get_session_service(session: DBSessionDep) -> SessionService:
    return SessionService(session)


def require_delete_sessions(
    user: User = Depends(require_manage_sessions)
) -> User:
    if user.role not in ("owner", "superAdmin"):
        from src.core.exceptions import PermissionDenied
        raise PermissionDenied(message="Requires one of roles: owner, superAdmin")
    return user


@router.get("", summary="List sessions")
async def list_sessions(
    actor: User = Depends(require_manage_sessions),
    service: SessionService = Depends(get_session_service),
    group_id: Optional[int] = Query(None, alias="groupId"),
    group_ids: Optional[list[int]] = Query(None, alias="groupIds"),  # ── Sprint 9
    branch_id: Optional[int] = Query(None, alias="branchId"),
    branch_ids_raw: Optional[str] = Query(None, alias="branchIds"),
    teacher_id: Optional[int] = Query(None, alias="teacherId"),
    room: Optional[str] = Query(None),
    date_from: date = Query(..., alias="dateFrom"),
    date_to: date = Query(..., alias="dateTo"),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=1000),
):
    parsed_branch_ids: Optional[list[int]] = None
    if branch_ids_raw and not branch_id:
        try:
            parsed_branch_ids = [int(x.strip()) for x in branch_ids_raw.split(",") if x.strip()]
        except ValueError:
            from fastapi import HTTPException
            raise HTTPException(status_code=422, detail="branchIds must be comma-separated integers")

    result = await service.list_sessions({
        "group_id": group_id, "group_ids": group_ids, "branch_id": branch_id, "branch_ids": parsed_branch_ids,
        "teacher_id": teacher_id, "room": room,
        "from_date": date_from, "to_date": date_to, "status": status,
        "page": page, "page_size": page_size,
    }, actor)
    return {"data": result}


@router.get("/{session_id}", summary="Get session by ID")
async def get_session(
    session_id: int,
    actor: User = Depends(get_current_user),  # ── Sprint 9: widened from require_manage_sessions
    service: SessionService = Depends(get_session_service),
):
    data = await service.get_session(session_id, actor)
    return {"data": data}


@router.patch("/{session_id}", summary="Update session")
async def update_session(
    session_id: int,
    body: UpdateSessionRequest,
    request: Request,
    actor: User = Depends(require_manage_sessions),
    service: SessionService = Depends(get_session_service),
):
    data = await service.update_session(
        session_id, body.model_dump(by_alias=False), actor,
        ip=request.client.host if request.client else None,
    )
    return {"data": data}


@router.delete("/{session_id}", summary="Delete session")
async def delete_session(
    session_id: int,
    request: Request,
    actor: User = Depends(require_delete_sessions),
    service: SessionService = Depends(get_session_service),
):
    await service.delete_session(
        session_id, actor,
        ip=request.client.host if request.client else None,
    )
    return {"data": {"deleted": True}}
