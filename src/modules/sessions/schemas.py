from datetime import date, datetime, time
from typing import Optional
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from src.modules.classes.schemas import TeacherBasic


class SessionResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    id: int
    group_id: int
    group_name: str
    class_id: int
    class_name: str
    module_name: str
    branch_id: int
    teacher: Optional[TeacherBasic] = None
    session_date: date
    start_time: time
    end_time: time
    room: str
    status: str
    original_session_id: Optional[int] = None
    notes: Optional[str] = None
    attendance_marked_at: Optional[datetime] = None
    attendance_marked_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class GenerateSessionsRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    group_id: int
    from_date: date
    weeks_ahead: Optional[int] = None


class GenerateSessionsResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    generated_count: int
    generated_until: date
    truncated_by_period_end: bool


class UpdateSessionRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    session_date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    room: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
