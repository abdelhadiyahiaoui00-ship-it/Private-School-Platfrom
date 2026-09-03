from typing import Optional

from fastapi import APIRouter, Depends, Query, Request

from src.core.database import DBSessionDep
from src.modules.assignments.schemas import (
    BulkCreateAssignmentRequest,
    CreateAssignmentRequest,
    SubmitAssignmentRequest,
    UpdateAssignmentRequest,
)
from src.modules.assignments.service import AssignmentService
from src.modules.auth.dependencies import get_current_user, require_manage_sessions, require_role
from src.modules.users.models import User
from src.modules.assignments.exceptions import AssignmentNotEnrolled

assignments_router = APIRouter(prefix="/assignments", tags=["Assignments"])
submissions_router = APIRouter(prefix="/assignments", tags=["Submissions"])
my_classes_router = APIRouter(prefix="/classes", tags=["Teacher Classes"])


def get_svc(session: DBSessionDep) -> AssignmentService:
    return AssignmentService(session)


def _is_admin(actor: User) -> bool:
    return actor.role in ("owner", "superAdmin") or (
        actor.role == "admin" and bool((actor.permissions or {}).get("manageClasses"))
    )


# ─── GET /api/assignments/my-submissions  (must be before /{id}) ──────────────
@submissions_router.get("/my-submissions", summary="Get my submissions")
async def get_my_submissions(
    actor: User = Depends(require_role(["student", "parent"])),
    svc: AssignmentService = Depends(get_svc),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=1000),
):
    return {"data": await svc.get_my_submissions(actor.id, page, page_size)}


# ─── POST /api/assignments/bulk-create  (must be before /{id}) ───────────────
@assignments_router.post("/bulk-create", status_code=201, summary="Bulk create assignments")
async def bulk_create(
    body: BulkCreateAssignmentRequest,
    request: Request,
    actor: User = Depends(require_manage_sessions),
    svc: AssignmentService = Depends(get_svc),
):
    ip = request.client.host if request.client else None
    return {"data": await svc.bulk_create_assignments(body, actor.id, _is_admin(actor), ip)}


# ─── DELETE /api/assignments/batch/:batch_id  (must be before /{id}) ─────────
@assignments_router.delete("/batch/{batch_id}", summary="Delete entire batch")
async def delete_batch(
    batch_id: str,
    request: Request,
    actor: User = Depends(require_manage_sessions),
    svc: AssignmentService = Depends(get_svc),
):
    ip = request.client.host if request.client else None
    return {"data": await svc.delete_batch(batch_id, actor.id, _is_admin(actor), ip)}


# ─── GET /api/assignments ─────────────────────────────────────────────────────
@assignments_router.get("", summary="List assignments")
async def list_assignments(
    actor: User = Depends(get_current_user),  # Sprint 9: widened from require_manage_sessions
    svc: AssignmentService = Depends(get_svc),
    search: Optional[str] = Query(None),
    class_id: Optional[int] = Query(None, alias="classId"),
    group_id: Optional[int] = Query(None, alias="groupId"),
    batch_id: Optional[str] = Query(None, alias="batchId"),
    due_status: str = Query("all", alias="dueStatus"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=1000),
    sort_by: str = Query("createdAt", alias="sortBy"),
    sort_order: str = Query("desc", alias="sortOrder"),
):
    filters = {"search": search, "classId": class_id, "groupId": group_id, "batchId": batch_id,
               "dueStatus": due_status, "sortBy": sort_by, "sortOrder": sort_order}
    return {"data": await svc.list_assignments(actor.id, _is_admin(actor), filters, page, page_size, actor=actor)}


# ─── POST /api/assignments ────────────────────────────────────────────────────
@assignments_router.post("", status_code=201, summary="Create assignment")
async def create_assignment(
    body: CreateAssignmentRequest,
    request: Request,
    actor: User = Depends(require_manage_sessions),
    svc: AssignmentService = Depends(get_svc),
):
    ip = request.client.host if request.client else None
    return {"data": await svc.create_assignment(body, actor.id, _is_admin(actor), ip)}


# ─── GET /api/assignments/:id ─────────────────────────────────────────────────
@assignments_router.get("/{assignment_id}", summary="Get assignment")
async def get_assignment(
    assignment_id: int,
    actor: User = Depends(require_manage_sessions),
    svc: AssignmentService = Depends(get_svc),
):
    return {"data": await svc.get_assignment(assignment_id, actor.id, _is_admin(actor))}


# ─── PATCH /api/assignments/:id ───────────────────────────────────────────────
@assignments_router.patch("/{assignment_id}", summary="Update assignment")
async def update_assignment(
    assignment_id: int,
    body: UpdateAssignmentRequest,
    request: Request,
    actor: User = Depends(require_manage_sessions),
    svc: AssignmentService = Depends(get_svc),
):
    ip = request.client.host if request.client else None
    return {"data": await svc.update_assignment(assignment_id, body, actor.id, _is_admin(actor), ip)}


# ─── DELETE /api/assignments/:id ──────────────────────────────────────────────
@assignments_router.delete("/{assignment_id}", summary="Delete assignment")
async def delete_assignment(
    assignment_id: int,
    request: Request,
    actor: User = Depends(require_manage_sessions),
    svc: AssignmentService = Depends(get_svc),
):
    ip = request.client.host if request.client else None
    await svc.delete_assignment(assignment_id, actor.id, _is_admin(actor), ip)
    return {"data": {"deleted": True}}


# ─── GET /api/assignments/:id/submissions ─────────────────────────────────────
@submissions_router.get("/{assignment_id}/submissions", summary="Get submissions roster")
async def get_submissions_roster(
    assignment_id: int,
    actor: User = Depends(require_manage_sessions),
    svc: AssignmentService = Depends(get_svc),
):
    return {"data": await svc.get_submissions_roster(assignment_id, actor.id, _is_admin(actor))}


# ─── POST /api/assignments/:id/submit ─────────────────────────────────────────
@submissions_router.post("/{assignment_id}/submit", summary="Submit assignment")
async def submit_assignment(
    assignment_id: int,
    body: SubmitAssignmentRequest,
    request: Request,
    actor: User = Depends(get_current_user),
    svc: AssignmentService = Depends(get_svc),
):
    ip = request.client.host if request.client else None
    student_id = body.student_id if actor.role == "parent" and body.student_id else actor.id
    return {"data": await svc.submit_assignment(assignment_id, student_id, body, actor.id, ip)}


# ─── GET /api/classes/my ──────────────────────────────────────────────────────
@my_classes_router.get("/my", summary="Get my classes (teacher)")
async def get_my_classes(
    actor: User = Depends(require_role(["teacher"])),
    svc: AssignmentService = Depends(get_svc),
):
    return {"data": await svc.get_my_classes(actor.id)}
