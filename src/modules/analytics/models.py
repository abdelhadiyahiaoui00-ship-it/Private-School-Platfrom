from decimal import Decimal
from typing import Optional
from sqlalchemy import ForeignKey, Integer, Numeric, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.common.base_model import BaseModel


class AnalyticsMonthlySnapshot(BaseModel):
    __tablename__ = "analytics_monthly_snapshots"

    branch_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("branches.id"), nullable=True, index=True
    )
    year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    month: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    total_revenue: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0.00)
    total_commissions: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0.00)
    net_revenue: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0.00)
    payment_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    new_enrollments: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active_subscriptions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    branch = relationship("Branch", lazy="selectin")


class AnalyticsTeacherMonthlySnapshot(BaseModel):
    __tablename__ = "analytics_teacher_monthly_snapshots"

    teacher_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    branch_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("branches.id"), nullable=True, index=True
    )
    year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    month: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    total_revenue: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0.00)
    total_commissions: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0.00)
    net_revenue: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0.00)
    session_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    student_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    payment_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    teacher = relationship("User", foreign_keys=[teacher_id], lazy="selectin")
    branch = relationship("Branch", foreign_keys=[branch_id], lazy="selectin")
