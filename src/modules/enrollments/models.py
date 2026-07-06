from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from src.common.base_model import BaseModel


class Enrollment(BaseModel):
    __tablename__ = "enrollments"

    group_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("groups.id"), nullable=False, index=True
    )
    branch_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("branches.id"), nullable=False, index=True
    )
    student_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True
    )
    # 'pending' | 'waitlisted' | 'active' | 'cancelled' | 'completed'
    waitlist_position: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    # 'self' | 'parent' | 'admin' | 'visitor_form'
    enrolled_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    activated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancelled_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
