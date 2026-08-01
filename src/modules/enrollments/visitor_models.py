from datetime import date, datetime
from typing import Optional
from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.core.database import Base


class VisitorEnrollmentRequest(Base):
    __tablename__ = "visitor_enrollment_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    enrollment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("enrollments.id", ondelete="CASCADE"), nullable=False
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    gender: Mapped[str] = mapped_column(String(10), nullable=False)
    contact_phone: Mapped[str] = mapped_column(String(30), nullable=False)
    contact_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    guardian_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    guardian_phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    # 'pending' | 'converted' | 'rejected'
    converted_to_user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    enrollment = relationship("Enrollment", back_populates="visitor_request")
