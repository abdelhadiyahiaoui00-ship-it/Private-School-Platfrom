"""
Users router — Sprint 1.
All endpoints follow { "data": ... } envelope.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request

from src.modules.auth.dependencies import (
    CurrentUser,
    require_role,
    require_manage_users,
)
from src.modules.users.models import User
from src.modules.users.dependencies import get_user_service
from src.modules.users.schemas import (
    BulkActionRequest,
    BulkActionResponse,
    CreateParentLinkRequest,
    CreateUserRequest,
    ParentLinkResponse,
    SetStatusRequest,
    UpdateUserRequest,
    UserDetailResponse,
    UserListResponse,
    UserResponse,
    UserWithPasswordResponse,
)
from src.modules.users.service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


# ─── List ─────────────────────────────────────────────────────────────────────

@router.get("", summary="List users (paginated + filtered)")
async def list_users(
    actor: User = Depends(require_manage_users),
    service: UserService = Depends(get_user_service),
    role: str = Query("all"),
    status: str = Query("all"),
    branch_id: Optional[int] = Query(None, alias="branchId"),
    search: str = Query(""),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, alias="pageSize", ge=1, le=100),
    sort_by: str = Query("createdAt", alias="sortBy"),
    sort_order: str = Query("desc", alias="sortOrder"),
):
    result = await service.list_users(
        actor=actor,
        role=role or None,
        status=status or None,
        branch_id=branch_id,
        search=search or None,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    from src.modules.users.schemas import PaginationMeta, UserStats

    items_out = [UserResponse.model_validate(u).model_dump(by_alias=True) for u in result["items"]]
    pagination_out = PaginationMeta(**result["pagination"]).model_dump(by_alias=True)
    stats_out = UserStats(**result["stats"]).model_dump(by_alias=True)

    return {"data": {"items": items_out, "pagination": pagination_out, "stats": stats_out}}


# ─── Create ───────────────────────────────────────────────────────────────────

@router.post("", status_code=201, summary="Create a user")
async def create_user(
    body: CreateUserRequest,
    request: Request,
    actor: User = Depends(require_manage_users),
    service: UserService = Depends(get_user_service),
):
    result = await service.create_user(
        body.model_dump(by_alias=False),
        actor,
        ip=request.client.host if request.client else None,
    )
    return {"data": result.model_dump(by_alias=True)}


# ─── Bulk ─────────────────────────────────────────────────────────────────────

@router.post("/bulk", summary="Bulk action on users")
async def bulk_action(
    body: BulkActionRequest,
    request: Request,
    actor: User = Depends(require_manage_users),
    service: UserService = Depends(get_user_service),
):
    result = await service.bulk_action(
        body.action,
        body.user_ids,
        actor,
        ip=request.client.host if request.client else None,
    )
    return {"data": BulkActionResponse(**result).model_dump(by_alias=True)}


# ─── Get single ───────────────────────────────────────────────────────────────

@router.get("/{user_id}", summary="Get user by ID")
async def get_user(
    user_id: int,
    actor: User = Depends(require_manage_users),
    service: UserService = Depends(get_user_service),
):
    user = await service.get_user(user_id, actor)
    return {"data": UserResponse.model_validate(user).model_dump(by_alias=True)}


# ─── Update ───────────────────────────────────────────────────────────────────

@router.patch("/{user_id}", summary="Update user")
async def update_user(
    user_id: int,
    body: UpdateUserRequest,
    request: Request,
    actor: User = Depends(require_manage_users),
    service: UserService = Depends(get_user_service),
):
    result = await service.update_user(
        user_id,
        body.model_dump(exclude_none=True, by_alias=False),
        actor,
        ip=request.client.host if request.client else None,
    )
    return {"data": result.model_dump(by_alias=True)}


# ─── Status ───────────────────────────────────────────────────────────────────

@router.patch("/{user_id}/status", summary="Set user status")
async def set_status(
    user_id: int,
    body: SetStatusRequest,
    request: Request,
    actor: User = Depends(require_manage_users),
    service: UserService = Depends(get_user_service),
):
    result = await service.set_status(
        user_id,
        body.status,
        actor,
        ip=request.client.host if request.client else None,
    )
    return {"data": result}


# ─── Reset password ───────────────────────────────────────────────────────────

@router.post("/{user_id}/reset-password", summary="Reset user password")
async def reset_password(
    user_id: int,
    request: Request,
    actor: User = Depends(require_manage_users),
    service: UserService = Depends(get_user_service),
):
    temp_password = await service.reset_password(
        user_id,
        actor,
        ip=request.client.host if request.client else None,
    )
    return {"data": {"temporaryPassword": temp_password}}


# ─── Delete ───────────────────────────────────────────────────────────────────

@router.delete("/{user_id}", summary="Delete user")
async def delete_user(
    user_id: int,
    request: Request,
    actor: User = Depends(require_manage_users),
    service: UserService = Depends(get_user_service),
):
    await service.delete_user(
        user_id,
        actor,
        ip=request.client.host if request.client else None,
    )
    return {"data": {"deleted": True}}


# ─── Print info ───────────────────────────────────────────────────────────────

@router.get("/{user_id}/print-info", summary="Get print account info")
async def get_print_info(
    user_id: int,
    actor: CurrentUser,
    service: UserService = Depends(get_user_service),
):
    result = await service.get_print_info(user_id, actor)
    return {"data": result}


# ─── Parent links ─────────────────────────────────────────────────────────────

parent_links_router = APIRouter(prefix="/parent-links", tags=["Parent Links"])


@parent_links_router.post("", status_code=201, summary="Create parent-student link")
async def create_parent_link(
    body: CreateParentLinkRequest,
    request: Request,
    actor: User = Depends(require_manage_users),
    service: UserService = Depends(get_user_service),
):
    link = await service.create_parent_link(
        body.parent_id,
        body.student_id,
        body.relationship,
        actor,
        ip=request.client.host if request.client else None,
    )
    return {"data": ParentLinkResponse.model_validate(link).model_dump(by_alias=True)}


@parent_links_router.delete("/{link_id}", summary="Remove parent-student link")
async def delete_parent_link(
    link_id: int,
    request: Request,
    actor: User = Depends(require_manage_users),
    service: UserService = Depends(get_user_service),
):
    await service.delete_parent_link(
        link_id,
        actor,
        ip=request.client.host if request.client else None,
    )
    return {"data": {"deleted": True}}
