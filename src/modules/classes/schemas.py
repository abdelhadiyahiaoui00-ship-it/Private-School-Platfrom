from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class LevelTargetingSchema(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    education_stage: str
    education_year: Optional[int] = None
    level_scope: str
    min_age: Optional[int] = None
    max_age: Optional[int] = None
    university_label: Optional[str] = None
    level_rank: Optional[int] = None


class TeacherBasic(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    id: int
    first_name: str
    last_name: str
    avatar_url: Optional[str] = None
    default_commission_percent: Optional[float] = None


class GroupSummary(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    id: int
    name: str
    schedule_summary: str
    max_students: int


class ClassResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    id: int
    branch_id: int
    branch_name: str
    module_id: int
    module_name: str
    module_color: Optional[str] = None
    teacher: TeacherBasic
    name: str
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    commission_percent: Optional[float] = None
    effective_commission_percent: float
    level: LevelTargetingSchema
    status: str
    groups_count: int
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class ClassDetailResponse(ClassResponse):
    groups_summary: list[GroupSummary] = []


class CreateClassRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    branch_id: int
    module_id: int
    teacher_id: int
    name: str
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    commission_percent: Optional[float] = None
    education_stage: str = "all"
    education_year: Optional[int] = None
    level_scope: str = "all_levels"
    min_age: Optional[int] = None
    max_age: Optional[int] = None
    university_label: Optional[str] = None


class UpdateClassRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    module_id: Optional[int] = None
    teacher_id: Optional[int] = None
    name: Optional[str] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    commission_percent: Optional[float] = None
    education_stage: Optional[str] = None
    education_year: Optional[int] = None
    level_scope: Optional[str] = None
    min_age: Optional[int] = None
    max_age: Optional[int] = None
    university_label: Optional[str] = None


class SetClassStatusRequest(BaseModel):
    status: str  # 'active' | 'archived'
    cascade_groups: bool = False
