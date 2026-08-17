from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from src.modules.enrollments.schemas import StudentBasic


class AttendanceRecordResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    student_id: int
    status: Optional[str] = None
    session_consumed: bool
    is_override: bool
    marked_at: Optional[datetime] = None
    marked_by_name: Optional[str] = None


class SubscriptionBalanceSummary(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    has_active_subscription: bool
    type: Optional[str] = None
    remaining_sessions: Optional[int] = None
    total_sessions: Optional[int] = None
    end_date: Optional[date] = None
    is_expiring_soon: bool
    is_expired: bool


class RosterEntry(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    student: StudentBasic
    is_currently_enrolled: bool
    subscription: SubscriptionBalanceSummary
    attendance: Optional[AttendanceRecordResponse] = None
    can_mark_present: bool


class AttendanceSummary(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    present_count: int
    absent_count: int
    excused_count: int
    unmarked_count: int
    total: int


class AttendanceRosterResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    session: dict
    can_mark_attendance: bool
    roster: list[RosterEntry]
    summary: AttendanceSummary


class MatrixSessionColumn(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: int
    session_date: date
    start_time: str
    end_time: str
    status: str


class MatrixCell(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    session_id: int
    status: Optional[str] = None
    session_consumed: bool
    is_override: bool


class MatrixStudentRow(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    student: StudentBasic
    is_currently_enrolled: bool
    subscription: SubscriptionBalanceSummary
    can_mark_present: bool
    cells: list[MatrixCell]
    present_count_in_window: int


class AttendanceMatrixResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    group_id: int
    group_name: str
    class_name: str
    module_name: str
    teacher_name: str
    branch_name: str
    sessions: list[MatrixSessionColumn]
    students: list[MatrixStudentRow]
    date_range_label: str
    has_next_page: bool
    has_prev_page: bool


class AttendanceRecordIn(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    student_id: int
    status: str
    override_present: bool = False


class MarkAttendanceRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    records: list[AttendanceRecordIn]
