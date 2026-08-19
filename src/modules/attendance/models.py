from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.common.base_model import BaseModel


class Attendance(BaseModel):
    __tablename__ = "attendance"

    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    student_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(10), nullable=False)
    session_consumed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_override: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    marked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=True
    )
    marked_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )

    student = relationship("User", foreign_keys=[student_id], lazy="selectin")
    marker = relationship("User", foreign_keys=[marked_by], lazy="selectin")

    __table_args__ = (
        CheckConstraint(
            "status IN ('present', 'absent', 'excused')",
            name="chk_attendance_status",
        ),
        Index("idx_attendance_session_student", "session_id", "student_id"),
    )
