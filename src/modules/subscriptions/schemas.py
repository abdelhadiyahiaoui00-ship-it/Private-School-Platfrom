from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from src.modules.enrollments.schemas import StudentBasic
from src.modules.classes.schemas import TeacherBasic
from src.modules.payments.schemas import PaymentResponse


class ExtensionLogEntry(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    date: datetime
    days_added: Optional[int] = None
    sessions_added: Optional[int] = None
    reason: str
    applied_by: int
    applied_by_name: str
    session_id: Optional[int] = None  # Sprint 7 will populate this


class SubscriptionResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    id: int
    enrollment_id: int
    student_id: int
    student: StudentBasic
    group_id: int
    group_name: str
    class_id: int
    class_name: str
    module_id: int
    module_name: str
    branch_id: int
    branch_name: str
    teacher_id: int
    teacher: TeacherBasic
    type: str                          # 'monthly' | 'session_based'
    status: str                        # 'active' | 'cancelled'
    # Monthly (null for session_based)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    # Session-based (null for monthly)
    total_sessions: Optional[int] = None
    remaining_sessions: Optional[int] = None
    # Financial ledger snapshot
    price: float
    commission_percent: Optional[float] = None
    commission_amount: Optional[float] = None
    net_amount: Optional[float] = None
    # Computed read-time flags (never stored)
    is_expiring_soon: bool
    is_expired: bool
    is_latest_for_enrollment: bool
    # History
    extension_log: list[ExtensionLogEntry] = []
    created_at: datetime
    updated_at: datetime
    activated_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancelled_reason: Optional[str] = None


class SubscriptionDetailResponse(SubscriptionResponse):
    payment: Optional[PaymentResponse] = None
    enrollment_source: str   # 'self'|'parent'|'admin'|'visitor_form'


class SubscriptionStats(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    total: int
    active: int
    expiring_soon: int
    expired: int
    cancelled: int


class ConfirmPaymentRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    amount: float
    method: str = "cash"              # 'cash' | 'other'
    notes: Optional[str] = None
    start_date: Optional[date] = None   # monthly only; defaults to today
    duration_days: Optional[int] = None # monthly only; defaults to system_config.monthlyDefaultDurationDays
    total_sessions: Optional[int] = None # session_based only; defaults to group.sessionCount


class RenewSubscriptionRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    amount: float
    method: str = "cash"
    notes: Optional[str] = None
    start_date: Optional[date] = None
    duration_days: Optional[int] = None
    total_sessions: Optional[int] = None


class ExtendSubscriptionRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    days_to_add: Optional[int] = None
    sessions_to_add: Optional[int] = None
    reason: str
    session_id: Optional[int] = None  # Sprint 7 wires this


class BulkExtendRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    days_to_add: Optional[int] = None
    sessions_to_add: Optional[int] = None
    reason: str
    session_id: Optional[int] = None


class CancelSubscriptionRequest(BaseModel):
    reason: Optional[str] = None



