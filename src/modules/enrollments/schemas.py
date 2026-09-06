from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class StudentBasic(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    id: int
    first_name: str
    last_name: str
    avatar_url: Optional[str] = None
    date_of_birth: Optional[date] = None


class EnrollmentResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    id: int
    group_id: int
    group_name: str
    class_id: int
    class_name: str
    module_name: str
    branch_id: int
    branch_name: str
    student_id: Optional[int] = None
    student: Optional[StudentBasic] = None
    status: str
    waitlist_position: Optional[int] = None
    source: str
    enrolled_by: Optional[int] = None
    is_overdue: bool
    reservation_expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    activated_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancelled_reason: Optional[str] = None


class EnrollmentDetailResponse(EnrollmentResponse):
    visitor_request: Optional["VisitorEnrollmentRequestBasic"] = None


class VisitorEnrollmentRequestBasic(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    id: int
    first_name: str
    last_name: str
    contact_phone: str
    contact_email: Optional[str] = None
    status: str


class VisitorEnrollmentRequestResponse(VisitorEnrollmentRequestBasic):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    enrollment_id: int
    date_of_birth: date
    gender: str
    guardian_name: Optional[str] = None
    guardian_phone: Optional[str] = None
    notes: Optional[str] = None
    converted_to_user_id: Optional[int] = None
    created_at: datetime
    enrollment: EnrollmentResponse


class EnrollmentStats(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    pending_count: int
    waitlisted_count: int
    overdue_count: int


class VisitorRequestStats(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    pending: int
    converted: int
    rejected: int


class ChildBasicResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    id: int
    first_name: str
    last_name: str
    avatar_url: Optional[str] = None
    date_of_birth: Optional[date] = None
    relationship: str
    link_id: int
    summary: Optional[dict] = None  # Sprint 10: per-child aggregated summary


class TransferPreviewResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    mode: str  # "active_transfer" | "pending_reenroll"
    eligible: bool
    reason: Optional[str] = None  # error code if not eligible
    target_group: dict
    preserved_subscription_id: Optional[int] = None  # active-path only
    resulting_status: Optional[str] = None  # pending-path only
    resulting_waitlist_position: Optional[int] = None  # pending-path only


class TransferGroupRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    target_group_id: int


class TransferGroupResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    enrollment: EnrollmentResponse
    subscription: Optional[dict] = None  # present on active-path only
    source_group_fifo_promoted_count: int


class CreateVisitorReservationRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    group_id: int
    first_name: str
    last_name: str
    date_of_birth: date
    gender: str
    contact_phone: str
    contact_email: Optional[str] = None
    guardian_name: Optional[str] = None
    guardian_phone: Optional[str] = None
    notes: Optional[str] = None


class CreateEnrollmentRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    group_id: int
    student_id: Optional[int] = None


class CancelEnrollmentRequest(BaseModel):
    reason: Optional[str] = None


class ConvertVisitorStudentDTO(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    gender: Optional[str] = None
    date_of_birth: Optional[date] = None
    language: str = "ar"


class ConvertVisitorParentDTO(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    first_name: str
    last_name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    relationship: str = "parent"


class ConvertVisitorRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    student: ConvertVisitorStudentDTO
    parent_action: str  # 'none' | 'linkExisting' | 'createNew'
    parent: Optional[ConvertVisitorParentDTO] = None
    existing_parent_id: Optional[int] = None


class RejectVisitorRequest(BaseModel):
    reason: Optional[str] = None
