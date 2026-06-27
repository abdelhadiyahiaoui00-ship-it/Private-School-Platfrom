from typing import Optional
from fastapi import APIRouter, Depends, Query, Request

from src.core.database import DBSessionDep
from src.modules.auth.dependencies import CurrentUser, require_role
from src.modules.branches.schemas import (
    BranchBasicResponse,
    BranchResponse,
    CreateBranchRequest,
    SetBranchStatusRequest,
    UpdateBranchRequest,
)
from src.modules.branches.service import BranchService
from src.modules.users.models import User

router = APIRouter(prefix="/branches", tags=["Branches"])


def get_branch_service(session: DBSessionDep) -> BranchService:
    return BranchService(session)


def require_owner_or_superadmin(
    user: User = Depends(require_role(["owner", "superAdmin"]))
) -> User:
    return user


def require_branch_read(
    user: User = Depends(require_role(["owner", "superAdmin", "admin"]))
) -> User:
    return user


# ─── GET /branches/my ─────────────────────────────────────────────────────────

@router.get("/my", summary="Get branches accessible to current user")
async def get_my_branches(
    actor: CurrentUser,
    service: BranchService = Depends(get_branch_service),
):
    """
    - owner / superAdmin: returns ALL branches (including inactive)
    - admin: returns only their assigned active branches
    - teacher/student/parent: returns empty list
    """
    if actor.role not in ("owner", "superAdmin", "admin"):
        return {"data": {"items": []}}

    branches = await service.get_my_branches(actor)
    items = [
        BranchBasicResponse.model_validate(b).model_dump(by_alias=True)
        for b in branches
    ]
    return {"data": {"items": items}}


# ─── GET /branches ────────────────────────────────────────────────────────────

@router.get("", summary="List branches (paginated)")
async def list_branches(
    actor: User = Depends(require_branch_read),
    service: BranchService = Depends(get_branch_service),
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None, alias="isActive"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=100),
):
    result = await service.list_branches(
        search=search or None,
        is_active=is_active,
        page=page,
        page_size=page_size,
    )
    items_out = [b.model_dump(by_alias=True) for b in result["items"]]
    return {
        "data": {
            "items": items_out,
            "pagination": result["pagination"],
            "stats": result["stats"],
        }
    }


# ─── GET /branches/:id ────────────────────────────────────────────────────────

@router.get("/{branch_id}", summary="Get branch by ID")
async def get_branch(
    branch_id: int,
    actor: User = Depends(require_branch_read),
    service: BranchService = Depends(get_branch_service),
):
    branch = await service.get_branch(branch_id)
    return {"data": branch.model_dump(by_alias=True)}


# ─── POST /branches ───────────────────────────────────────────────────────────

@router.post("", status_code=201, summary="Create branch")
async def create_branch(
    body: CreateBranchRequest,
    request: Request,
    actor: User = Depends(require_owner_or_superadmin),
    service: BranchService = Depends(get_branch_service),
):
    branch = await service.create_branch(
        body.model_dump(by_alias=False),
        actor,
        ip=request.client.host if request.client else None,
    )
    return {"data": branch.model_dump(by_alias=True)}


# ─── PATCH /branches/:id ──────────────────────────────────────────────────────

@router.patch("/{branch_id}", summary="Update branch")
async def update_branch(
    branch_id: int,
    body: UpdateBranchRequest,
    request: Request,
    actor: User = Depends(require_owner_or_superadmin),
    service: BranchService = Depends(get_branch_service),
):
    branch = await service.update_branch(
        branch_id,
        body.model_dump(exclude_none=True, by_alias=False),
        actor,
        ip=request.client.host if request.client else None,
    )
    return {"data": branch.model_dump(by_alias=True)}


# ─── PATCH /branches/:id/status ───────────────────────────────────────────────

@router.patch("/{branch_id}/status", summary="Set branch active/inactive")
async def set_branch_status(
    branch_id: int,
    body: SetBranchStatusRequest,
    request: Request,
    actor: User = Depends(require_owner_or_superadmin),
    service: BranchService = Depends(get_branch_service),
):
    result = await service.set_status(
        branch_id,
        body.is_active,
        actor,
        ip=request.client.host if request.client else None,
    )
    return {"data": result}


# ─── DELETE /branches/:id ─────────────────────────────────────────────────────

@router.delete("/{branch_id}", summary="Delete branch")
async def delete_branch(
    branch_id: int,
    request: Request,
    actor: User = Depends(require_owner_or_superadmin),
    service: BranchService = Depends(get_branch_service),
):
    await service.delete_branch(
        branch_id,
        actor,
        ip=request.client.host if request.client else None,
    )
    return {"data": {"deleted": True}}
