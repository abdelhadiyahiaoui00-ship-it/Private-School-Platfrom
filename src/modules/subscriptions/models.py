from datetime import date, datetime
from typing import Optional
from sqlalchemy import (
    DateTime, Date, ForeignKey, Integer, JSON,
    Numeric, String, Text, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.common.base_model import BaseModel


class Subscription(BaseModel):
    __tablename__ = "subscriptions"

    enrollment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("enrollments.id"), nullable=False, index=True
    )
    student_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    group_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("groups.id"), nullable=False, index=True
    )
    branch_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("branches.id"), nullable=False
    )
    # Denormalized snapshots (set at creation, never updated)
    teacher_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    module_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("modules.id"), nullable=True
    )
    # Type: 'monthly' | 'session_based'
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    # Status: 'active' | 'cancelled' ONLY
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    # Financial ledger (snapshot at creation)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    commission_percent: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    commission_amount: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    net_amount: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    # Monthly fields
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    # Session-based fields
    total_sessions: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    remaining_sessions: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # Extension log: [{date, daysAdded|sessionsAdded, reason, appliedBy, appliedByName, sessionId}]
    extension_log: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # Audit
    activated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancelled_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships (lazy selectin for API reads)
    student = relationship("User", foreign_keys=[student_id], lazy="selectin")
    teacher = relationship("User", foreign_keys=[teacher_id], lazy="selectin")
    group = relationship("Group", lazy="selectin")
    branch = relationship("Branch", lazy="selectin")
    payment = relationship(
        "Payment",
        back_populates="subscription",
        uselist=False,
        lazy="selectin",
    )
