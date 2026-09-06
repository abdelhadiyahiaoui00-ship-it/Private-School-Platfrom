from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from src.modules.enrollments.schemas import StudentBasic
from src.modules.classes.schemas import TeacherBasic


class PaymentResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    id: int
    subscription_id: int
    enrollment_id: Optional[int] = None
    student_id: int
    student: StudentBasic
    branch_id: int
    branch_name: str
    class_id: Optional[int] = None
    module_id: Optional[int] = None
    module_name: str
    class_name: str
    group_name: str
    teacher_id: Optional[int] = None
    teacher: TeacherBasic
    amount: float
    currency: str
    method: str
    commission_percent: Optional[float] = None
    commission_amount: Optional[float] = None
    net_amount: Optional[float] = None
    payment_type: str                  # 'initial' | 'renewal'
    recorded_by: int
    recorded_by_name: str
    recorded_at: datetime
    notes: Optional[str] = None


class PaymentSummary(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    total_amount: float
    total_commission: float
    total_net: float
    count: int
