from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class RescheduleRequestResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: int
    session_id: int
    session: dict
    requested_by: int
    requested_by_name: str
    reason: str
    proposed_date: date
    proposed_start_time: str
    proposed_end_time: str
    proposed_room: Optional[str] = None
    status: str
    reviewed_by: Optional[int] = None
    reviewed_by_name: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: datetime


class CreateRescheduleRequestBody(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    reason: str
    proposed_date: date
    proposed_start_time: str
    proposed_end_time: str
    proposed_room: Optional[str] = None


class ApproveRescheduleBody(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class RejectRescheduleBody(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    reason: str


class DirectRescheduleBody(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    new_date: date
    new_start_time: str
    new_end_time: str
    new_room: Optional[str] = None
    reason: Optional[str] = None


class MarkTeacherAbsentBody(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    reason: Optional[str] = None
