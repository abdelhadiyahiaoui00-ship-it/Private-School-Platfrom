from typing import Optional
from fastapi import APIRouter, Depends, Query, Request

from src.core.database import DBSessionDep
from src.modules.auth.dependencies import require_role
from src.modules.modules.schemas import (
    CreateModuleRequest, SetModuleStatusRequest, UpdateModuleRequest
)
from src.modules.modules.service import ModuleService
from src.modules.users.models import User

router = APIRouter(prefix="/modules", tags=["Modules"])


def get_module_service(session: DBSessionDep) -> ModuleService:
    return ModuleService(session)


def require_manage_classes(user: User = Depends(require_role(["owner", "superAdmin", "admin"]))) -> User:
    if user.role in ("owner", "superAdmin"):
        return user
    perms = user.permissions or {}
    if perms.get("manageClasses"):
        return user
    from src.core.exceptions import PermissionDenied
    raise PermissionDenied(message="Requires manageClasses permission.")


@router.get("", summary="List modules")
async def list_modules(
    actor: User = Depends(require_manage_classes),
    service: ModuleService = Depends(get_module_service),
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None, alias="isActive"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=100),
):
    result = await service.list_modules(
        search=search, category=category, is_active=is_active,
        page=page, page_size=page_size,
    )
    return {"data": result}


@router.get("/categories", summary="Get distinct module categories")
async def get_categories(
    actor: User = Depends(require_manage_classes),
    service: ModuleService = Depends(get_module_service),
):
    categories = await service.get_categories()
    return {"data": {"categories": categories}}


@router.get("/{module_id}", summary="Get module by ID")
async def get_module(
    module_id: int,
    actor: User = Depends(require_manage_classes),
    service: ModuleService = Depends(get_module_service),
):
    data = await service.get_module(module_id)
    return {"data": data}


@router.post("", status_code=201, summary="Create module")
async def create_module(
    body: CreateModuleRequest,
    request: Request,
    actor: User = Depends(require_manage_classes),
    service: ModuleService = Depends(get_module_service),
):
    data = await service.create_module(
        body.model_dump(by_alias=False),
        actor,
        ip=request.client.host if request.client else None,
    )
    return {"data": data}


@router.patch("/{module_id}", summary="Update module")
async def update_module(
    module_id: int,
    body: UpdateModuleRequest,
    request: Request,
    actor: User = Depends(require_manage_classes),
    service: ModuleService = Depends(get_module_service),
):
    data = await service.update_module(
        module_id,
        body.model_dump(exclude_none=True, by_alias=False),
        actor,
        ip=request.client.host if request.client else None,
    )
    return {"data": data}


@router.patch("/{module_id}/status", summary="Set module active/inactive")
async def set_module_status(
    module_id: int,
    body: SetModuleStatusRequest,
    request: Request,
    actor: User = Depends(require_manage_classes),
    service: ModuleService = Depends(get_module_service),
):
    data = await service.set_status(
        module_id, body.is_active, actor,
        ip=request.client.host if request.client else None,
    )
    return {"data": data}


@router.delete("/{module_id}", summary="Delete module")
async def delete_module(
    module_id: int,
    request: Request,
    actor: User = Depends(require_manage_classes),
    service: ModuleService = Depends(get_module_service),
):
    await service.delete_module(
        module_id, actor,
        ip=request.client.host if request.client else None,
    )
    return {"data": {"deleted": True}}
