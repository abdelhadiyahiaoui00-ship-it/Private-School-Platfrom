from datetime import datetime, date
from decimal import Decimal
from typing import Generic, List, Optional, TypeVar, Union
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ItemsEnvelope(BaseModel, Generic[T]):
    items: List[T]


class ResponseWrapper(BaseModel, Generic[T]):
    data: Union[ItemsEnvelope[T], T]


class MonthlySnapshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    branch_id: Optional[int] = None
    year: int
    month: int
    total_revenue: Decimal
    total_commissions: Decimal
    net_revenue: Decimal
    payment_count: int
    new_enrollments: int
    active_subscriptions: int
    created_at: Optional[datetime] = None


class TeacherSnapshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    teacher_id: int
    branch_id: Optional[int] = None
    year: int
    month: int
    total_revenue: Decimal
    total_commissions: Decimal
    net_revenue: Decimal
    session_count: int
    student_count: int
    payment_count: int
    created_at: Optional[datetime] = None


class RevenueOverviewOut(BaseModel):
    total_revenue: Decimal
    total_commissions: Decimal
    net_revenue: Decimal
    payment_count: int
    year: int
    month: int
    branch_id: Optional[int] = None


class TopTeacherOut(BaseModel):
    teacher_id: int
    teacher_name: str
    total_revenue: Decimal
    net_revenue: Decimal
    payment_count: int


class BaseTrendPoint(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    granularity: str = "month"  # "day" | "month"
    day: Optional[int] = None   # 1-31 for day, None for month
    is_final: bool = Field(True, alias="isFinal")
    label: str
    year: int
    month: int


class RevenueTrendPoint(BaseTrendPoint):
    total_revenue: Decimal = Field(..., alias="totalRevenue")
    commission_total: Decimal = Field(Decimal("0.00"), alias="commissionTotal")
    net_revenue: Decimal = Field(..., alias="netRevenue")
    payment_count: int = Field(..., alias="paymentsCount")


class StudentsTrendPoint(BaseTrendPoint):
    active_students_count: int = Field(..., alias="activeStudentsCount")


class EnrollmentFunnelPoint(BaseTrendPoint):
    visitor_requests_count: int = Field(0, alias="visitorRequestsCount")
    visitor_requests_converted_count: int = Field(0, alias="visitorRequestsConvertedCount")
    enrollments_created_count: int = Field(0, alias="enrollmentsCreatedCount")
    enrollments_active_count: int = Field(0, alias="enrollmentsActiveCount")
    conversion_rate: float = Field(0.0, alias="conversionRate")


class OperationsTrendPoint(BaseTrendPoint):
    teacher_absences_count: int = Field(0, alias="teacherAbsencesCount")
    reschedules_approved_count: int = Field(0, alias="reschedulesApprovedCount")


class PaymentMethodBreakdownOut(BaseModel):
    method: str
    count: int
    total_amount: Decimal
    percentage: float


class BranchRevenueOut(BaseModel):
    branch_id: int
    branch_name: str
    total_revenue: Decimal
    net_revenue: Decimal
    payment_count: int


class DataExportRow(BaseModel):
    payment_id: int
    student_id: int
    student_name: str
    branch_id: int
    branch_name: str
    class_id: Optional[int] = None
    class_name: Optional[str] = None
    teacher_id: Optional[int] = None
    teacher_name: Optional[str] = None
    amount: Decimal
    commission_amount: Decimal
    net_amount: Decimal
    method: str
    payment_type: str
    recorded_at: datetime
