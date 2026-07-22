from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request

from src.core.database import DBSessionDep
from src.modules.auth.dependencies import require_role
from src.modules.sessions.schemas import (
    GenerateSessionsRequest, UpdateSessionRequest
)
from src.modules.sessions.service import SessionService
from src.modules.users.models import User

router = APIRouter(prefix="/sessions", tags=["Sessions"])


def get_session_service(session: DBSessionDep) -> SessionService:
    return SessionService(session)


def require_manage_sessions(user: User = Depends(require_role(["owner", "superAdmin", "admin"]))) -> User:
    if user.role in ("owner", "superAdmin"):
        return user
    perms = user.permissions or {}
    if perms.get("manageSessions"):
        return user
    from src.core.exceptions import PermissionDenied
    raise PermissionDenied(message="Requires manageSessions permission.")


@router.get("", summary="List sessions")
async def list_sessions(
    actor: User = Depends(require_manage_sessions),
    service: SessionService = Depends(get_session_service),
    group_id: Optional[int] = Query(None, alias="groupId"),
    branch_id: Optional[int] = Query(None, alias="branchId"),
    teacher_id: Optional[int] = Query(None, alias="teacherId"),
    room: Optional[str] = Query(None),
    from_date: Optional[date] = Query(None, alias="fromDate"),
    to_date: Optional[date] = Query(None, alias="toDate"),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=100),
):
    result = await service.list_sessions({
        "group_id": group_id, "branch_id": branch_id,
        "teacher_id": teacher_id, "room": room,
        "from_date": from_date, "to_date": to_date, "status": status,
        "page": page, "page_size": page_size,
    }, actor)
    return {"data": result}


@router.get("/{session_id}", summary="Get session by ID")
async def get_session(
    session_id: int,
    actor: User = Depends(require_manage_sessions),
    service: SessionService = Depends(get_session_service),
):
    data = await service.get_session(session_id, actor)
    return {"data": data}


@router.post("/generate", status_code=201, summary="Generate sessions")
async def generate_sessions_endpoint(
    body: GenerateSessionsRequest,
    request: Request,
    actor: User = Depends(require_manage_sessions),
    service: SessionService = Depends(get_session_service),
):
    data = await service.trigger_generation(
        body.group_id, body.from_date, body.weeks_ahead, actor,
        ip=request.client.host if request.client else None,
    )
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
        session_id, body.model_dump(exclude_none=True, by_alias=False), actor,
        ip=request.client.host if request.client else None,
    )
    return {"data": data}


@router.delete("/{session_id}", summary="Delete session")
async def delete_session(
    session_id: int,
    request: Request,
    actor: User = Depends(require_manage_sessions),
    service: SessionService = Depends(get_session_service),
):
    await service.delete_session(
        session_id, actor,
        ip=request.client.host if request.client else None,
    )
    return {"data": {"deleted": True}}
