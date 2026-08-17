from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request

from src.core.database import DBSessionDep
from src.modules.attendance.reschedule_schemas import (
    CreateRescheduleRequestBody,
    DirectRescheduleBody,
    MarkTeacherAbsentBody,
    RejectRescheduleBody,
)
from src.modules.attendance.reschedule_service import RescheduleService
from src.modules.attendance.schemas import MarkAttendanceRequest
from src.modules.attendance.service import AttendanceService
from src.modules.auth.dependencies import (
    require_manage_sessions,
    require_manage_sessions_admin_only,
)
from src.modules.users.models import User

attendance_router = APIRouter(prefix="/sessions", tags=["Attendance"])
reschedule_session_router = APIRouter(prefix="/sessions", tags=["Reschedule"])
reschedule_router = APIRouter(
    prefix="/reschedule-requests", tags=["Reschedule Requests"]
)
group_attendance_router = APIRouter(prefix="/groups", tags=["Attendance Matrix"])


def get_attendance_service(session: DBSessionDep) -> AttendanceService:
    return AttendanceService(session)


def get_reschedule_service(session: DBSessionDep) -> RescheduleService:
    return RescheduleService(session)


@attendance_router.get("/{session_id}/attendance", summary="Get attendance roster")
async def get_attendance_roster(
    session_id: int,
    actor: User = Depends(require_manage_sessions),
    service: AttendanceService = Depends(get_attendance_service),
):
    data = await service.get_roster(session_id, actor)
    return {"data": data}


@attendance_router.patch("/{session_id}/attendance", summary="Save attendance records")
async def save_attendance(
    session_id: int,
    body: MarkAttendanceRequest,
    request: Request,
    actor: User = Depends(require_manage_sessions),
    service: AttendanceService = Depends(get_attendance_service),
):
    ip = request.client.host if request.client else None
    data = await service.save_attendance(session_id, body.records, actor, ip=ip)
    return {"data": data}


@reschedule_session_router.patch(
    "/{session_id}/mark-teacher-absent",
    summary="Mark session as teacher absent",
)
async def mark_teacher_absent(
    session_id: int,
    body: MarkTeacherAbsentBody,
    request: Request,
    actor: User = Depends(require_manage_sessions_admin_only),
    service: RescheduleService = Depends(get_reschedule_service),
):
    ip = request.client.host if request.client else None
    data = await service.mark_teacher_absent(session_id, body.reason, actor, ip=ip)
    return {"data": data}


@reschedule_session_router.post(
    "/{session_id}/reschedule-requests",
    status_code=201,
    summary="Submit reschedule request",
)
async def create_reschedule_request(
    session_id: int,
    body: CreateRescheduleRequestBody,
    request: Request,
    actor: User = Depends(require_manage_sessions),
    service: RescheduleService = Depends(get_reschedule_service),
):
    ip = request.client.host if request.client else None
    data = await service.create_request(
        session_id, body.model_dump(by_alias=False), actor, ip=ip
    )
    return {"data": data}


@reschedule_session_router.patch(
    "/{session_id}/reschedule",
    summary="Admin direct reschedule",
)
async def direct_reschedule(
    session_id: int,
    body: DirectRescheduleBody,
    request: Request,
    actor: User = Depends(require_manage_sessions_admin_only),
    service: RescheduleService = Depends(get_reschedule_service),
):
    ip = request.client.host if request.client else None
    data = await service.direct_reschedule(
        session_id, body.model_dump(by_alias=False), actor, ip=ip
    )
    return {"data": data}


@reschedule_router.get("", summary="List reschedule requests")
async def list_reschedule_requests(
    actor: User = Depends(require_manage_sessions_admin_only),
    service: RescheduleService = Depends(get_reschedule_service),
    status: str = Query("pending"),
    branch_id: Optional[int] = Query(None, alias="branchId"),
    teacher_id: Optional[int] = Query(None, alias="teacherId"),
    group_id: Optional[int] = Query(None, alias="groupId"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=100),
):
    data = await service.list_requests(
        {
            "status": status,
            "branch_id": branch_id,
            "teacher_id": teacher_id,
            "group_id": group_id,
            "page": page,
            "page_size": page_size,
        },
        actor,
    )
    return {"data": data}


@reschedule_router.post("/{request_id}/approve", summary="Approve reschedule request")
async def approve_reschedule(
    request_id: int,
    request: Request,
    actor: User = Depends(require_manage_sessions_admin_only),
    service: RescheduleService = Depends(get_reschedule_service),
):
    ip = request.client.host if request.client else None
    data = await service.approve_request(request_id, actor, ip=ip)
    return {"data": data}


@reschedule_router.post("/{request_id}/reject", summary="Reject reschedule request")
async def reject_reschedule(
    request_id: int,
    body: RejectRescheduleBody,
    request: Request,
    actor: User = Depends(require_manage_sessions_admin_only),
    service: RescheduleService = Depends(get_reschedule_service),
):
    ip = request.client.host if request.client else None
    data = await service.reject_request(request_id, body.reason, actor, ip=ip)
    return {"data": data}


@group_attendance_router.get(
    "/{group_id}/attendance-matrix",
    summary="Get attendance matrix for a group",
)
async def get_attendance_matrix(
    group_id: int,
    actor: User = Depends(require_manage_sessions),
    service: AttendanceService = Depends(get_attendance_service),
    anchor_date: Optional[date] = Query(None, alias="anchorDate"),
    direction: str = Query("current"),
    page_size: int = Query(8, alias="pageSize", ge=1, le=30),
):
    data = await service.get_attendance_matrix(
        group_id,
        actor,
        anchor_date=anchor_date,
        direction=direction,
        page_size=page_size,
    )
    return {"data": data}
