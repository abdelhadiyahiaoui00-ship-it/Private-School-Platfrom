from datetime import datetime
from decimal import Decimal
from typing import Generic, List, Optional, TypeVar
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ResponseWrapper(BaseModel, Generic[T]):
    data: T


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


class RevenueTrendPoint(BaseModel):
    year: int
    month: int
    total_revenue: Decimal
    net_revenue: Decimal
    payment_count: int


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
