from datetime import date
from typing import Optional
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class PublicTeacherBasic(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    id: int
    first_name: str
    last_name: str
    avatar_url: Optional[str] = None
    # Note: email and phone NOT included — privacy


class PublicGroupResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    id: int
    name: str
    class_id: int
    class_name: str
    module_id: int
    module_name: str
    module_category: Optional[str] = None
    teacher: PublicTeacherBasic
    branch_id: int
    branch_name: str
    schedule: list[dict]         # [{dayOfWeek, startTime, endTime}]
    room: str
    price: float
    subscription_type: str       # 'monthly' | 'session_based'
    session_count: Optional[int] = None
    max_students: int
    active_enrollments: int
    is_full: bool
    available_seats: int


class PublicGroupDetailResponse(PublicGroupResponse):
    class_description: Optional[str] = None
    class_period_start: Optional[date] = None
    class_period_end: Optional[date] = None
    sessions_preview: list[dict] = []
    # [{date, startTime, endTime, room}] — next 3 upcoming sessions


class PublicBranchResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    id: int
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    map_embed_url: Optional[str] = None
    photo_urls: list[str] = []
    description: Optional[str] = None
    active_classes_count: int = 0
