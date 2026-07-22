from typing import Optional
from fastapi import APIRouter, Depends, Query, Request

from src.core.database import DBSessionDep
from src.modules.auth.dependencies import require_role
from src.modules.groups.schemas import (
    CreateGroupRequest, SetGroupStatusRequest, UpdateGroupRequest
)
from src.modules.groups.service import GroupService
from src.modules.users.models import User

router = APIRouter(prefix="/groups", tags=["Groups"])


def get_group_service(session: DBSessionDep) -> GroupService:
    return GroupService(session)


def require_manage_classes(user: User = Depends(require_role(["owner", "superAdmin", "admin"]))) -> User:
    if user.role in ("owner", "superAdmin"):
        return user
    perms = user.permissions or {}
    if perms.get("manageClasses"):
        return user
    from src.core.exceptions import PermissionDenied
    raise PermissionDenied(message="Requires manageClasses permission.")


@router.get("", summary="List groups")
async def list_groups(
    actor: User = Depends(require_manage_classes),
    service: GroupService = Depends(get_group_service),
    class_id: Optional[int] = Query(None, alias="classId"),
    branch_id: Optional[int] = Query(None, alias="branchId"),
    teacher_id: Optional[int] = Query(None, alias="teacherId"),
    status: str = Query("active"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=100),
):
    result = await service.list_groups({
        "class_id": class_id, "branch_id": branch_id,
        "teacher_id": teacher_id, "status": status,
        "page": page, "page_size": page_size,
    }, actor)
    return {"data": result}


@router.get("/{group_id}", summary="Get group by ID")
async def get_group(
    group_id: int,
    actor: User = Depends(require_manage_classes),
    service: GroupService = Depends(get_group_service),
):
    data = await service.get_group(group_id, actor)
    return {"data": data}


@router.post("", status_code=201, summary="Create group")
async def create_group(
    body: CreateGroupRequest,
    request: Request,
    actor: User = Depends(require_manage_classes),
    service: GroupService = Depends(get_group_service),
):
    data = await service.create_group(
        body.model_dump(by_alias=False), actor,
        ip=request.client.host if request.client else None,
    )
    return {"data": data}


@router.patch("/{group_id}", summary="Update group")
async def update_group(
    group_id: int,
    body: UpdateGroupRequest,
    request: Request,
    actor: User = Depends(require_manage_classes),
    service: GroupService = Depends(get_group_service),
):
    data = await service.update_group(
        group_id, body.model_dump(exclude_none=True, by_alias=False), actor,
        ip=request.client.host if request.client else None,
    )
    return {"data": data}


@router.patch("/{group_id}/status", summary="Set group status")
async def set_group_status(
    group_id: int,
    body: SetGroupStatusRequest,
    request: Request,
    actor: User = Depends(require_manage_classes),
    service: GroupService = Depends(get_group_service),
):
    data = await service.set_status(
        group_id, body.status, actor,
        ip=request.client.host if request.client else None,
    )
    return {"data": data}


@router.delete("/{group_id}", summary="Delete group")
async def delete_group(
    group_id: int,
    request: Request,
    actor: User = Depends(require_manage_classes),
    service: GroupService = Depends(get_group_service),
):
    await service.delete_group(
        group_id, actor,
        ip=request.client.host if request.client else None,
    )
    return {"data": {"deleted": True}}
