from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from src.modules.classes.schemas import TeacherBasic


class ScheduleSlot(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    day_of_week: int = Field(ge=0, le=6)
    start_time: str
    end_time: str


class GroupResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    id: int
    class_id: int
    class_name: str
    module_name: str
    name: str
    teacher: Optional[TeacherBasic] = None
    schedule: list[ScheduleSlot]
    room: str
    max_students: int
    price: float
    subscription_type: str
    session_count: Optional[int] = None
    status: str
    last_generated_until: Optional[date] = None
    created_at: datetime
    updated_at: datetime
    # Placeholders for Sprint 5
    active_enrollments: int = 0
    available_seats: int = 0


class CreateGroupRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    class_id: int
    name: str
    teacher_id: Optional[int] = None
    schedule: list[ScheduleSlot]
    room: str
    max_students: int
    price: float
    subscription_type: str
    session_count: Optional[int] = None


class UpdateGroupRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    name: Optional[str] = None
    teacher_id: Optional[int] = None
    schedule: Optional[list[ScheduleSlot]] = None
    room: Optional[str] = None
    max_students: Optional[int] = None
    price: Optional[float] = None
    subscription_type: Optional[str] = None
    session_count: Optional[int] = None


class SetGroupStatusRequest(BaseModel):
    status: str  # 'active' | 'archived'
