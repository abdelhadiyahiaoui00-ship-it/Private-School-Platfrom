from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.common.base_model import BaseModel


class Payment(BaseModel):
    __tablename__ = "payments"

    subscription_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("subscriptions.id"), nullable=False, unique=True
    )
    enrollment_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("enrollments.id"), nullable=True
    )
    student_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    branch_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("branches.id"), nullable=False
    )
    # Denormalized for Sprint 12 GROUP BY without joins
    class_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("classes.id"), nullable=True
    )
    module_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("modules.id"), nullable=True
    )
    teacher_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    # Financial
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="DZD")
    method: Mapped[str] = mapped_column(String(20), nullable=False, default="cash")
    commission_percent: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    commission_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    net_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    payment_type: Mapped[str] = mapped_column(String(20), nullable=False, default="initial")
    # 'initial' | 'renewal'
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recorded_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    subscription = relationship("Subscription", back_populates="payment", lazy="selectin")
    student = relationship("User", foreign_keys=[student_id], lazy="selectin")
    teacher = relationship("User", foreign_keys=[teacher_id], lazy="selectin")
    recorder = relationship("User", foreign_keys=[recorded_by], lazy="selectin")
    branch = relationship("Branch", foreign_keys=[branch_id], lazy="selectin")
    class_ = relationship("Class", foreign_keys=[class_id], lazy="selectin")
    module = relationship("Module", foreign_keys=[module_id], lazy="selectin")
