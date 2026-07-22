from typing import Optional
from fastapi import APIRouter, Depends, Query, Request

from src.core.database import DBSessionDep
from src.modules.auth.dependencies import require_role
from src.modules.classes.schemas import (
    CreateClassRequest, SetClassStatusRequest, UpdateClassRequest
)
from src.modules.classes.service import ClassService
from src.modules.users.models import User

router = APIRouter(prefix="/classes", tags=["Classes"])


def get_class_service(session: DBSessionDep) -> ClassService:
    return ClassService(session)


def require_manage_classes(user: User = Depends(require_role(["owner", "superAdmin", "admin"]))) -> User:
    if user.role in ("owner", "superAdmin"):
        return user
    perms = user.permissions or {}
    if perms.get("manageClasses"):
        return user
    from src.core.exceptions import PermissionDenied
    raise PermissionDenied(message="Requires manageClasses permission.")


@router.get("", summary="List classes")
async def list_classes(
    actor: User = Depends(require_manage_classes),
    service: ClassService = Depends(get_class_service),
    search: Optional[str] = Query(None),
    branch_id: Optional[int] = Query(None, alias="branchId"),
    module_id: Optional[int] = Query(None, alias="moduleId"),
    teacher_id: Optional[int] = Query(None, alias="teacherId"),
    status: str = Query("active"),
    education_stage: Optional[str] = Query(None, alias="educationStage"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=100),
    sort_by: str = Query("createdAt", alias="sortBy"),
    sort_order: str = Query("desc", alias="sortOrder"),
):
    result = await service.list_classes({
        "search": search, "branch_id": branch_id, "module_id": module_id,
        "teacher_id": teacher_id, "status": status, "education_stage": education_stage,
        "page": page, "page_size": page_size, "sort_by": sort_by, "sort_order": sort_order,
    }, actor)
    return {"data": result}


@router.get("/{class_id}", summary="Get class by ID")
async def get_class(
    class_id: int,
    actor: User = Depends(require_manage_classes),
    service: ClassService = Depends(get_class_service),
):
    data = await service.get_class(class_id, actor)
    return {"data": data}


@router.post("", status_code=201, summary="Create class")
async def create_class(
    body: CreateClassRequest,
    request: Request,
    actor: User = Depends(require_manage_classes),
    service: ClassService = Depends(get_class_service),
):
    data = await service.create_class(
        body.model_dump(by_alias=False), actor,
        ip=request.client.host if request.client else None,
    )
    return {"data": data}


@router.patch("/{class_id}", summary="Update class")
async def update_class(
    class_id: int,
    body: UpdateClassRequest,
    request: Request,
    actor: User = Depends(require_manage_classes),
    service: ClassService = Depends(get_class_service),
):
    data = await service.update_class(
        class_id, body.model_dump(exclude_none=True, by_alias=False), actor,
        ip=request.client.host if request.client else None,
    )
    return {"data": data}


@router.patch("/{class_id}/status", summary="Set class status")
async def set_class_status(
    class_id: int,
    body: SetClassStatusRequest,
    request: Request,
    actor: User = Depends(require_manage_classes),
    service: ClassService = Depends(get_class_service),
):
    data = await service.set_status(
        class_id, body.status, body.cascade_groups, actor,
        ip=request.client.host if request.client else None,
    )
    return {"data": data}


@router.delete("/{class_id}", summary="Delete class")
async def delete_class(
    class_id: int,
    request: Request,
    actor: User = Depends(require_manage_classes),
    service: ClassService = Depends(get_class_service),
):
    await service.delete_class(
        class_id, actor,
        ip=request.client.host if request.client else None,
    )
    return {"data": {"deleted": True}}
