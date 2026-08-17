from datetime import date, datetime, time
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, Time, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.common.base_model import BaseModel


class SessionRescheduleRequest(BaseModel):
    __tablename__ = "session_reschedule_requests"

    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sessions.id"), nullable=False, index=True
    )
    requested_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    proposed_date: Mapped[date] = mapped_column(Date, nullable=False)
    proposed_start_time: Mapped[time] = mapped_column(Time, nullable=False)
    proposed_end_time: Mapped[time] = mapped_column(Time, nullable=False)
    proposed_room: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    reviewed_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    requester = relationship("User", foreign_keys=[requested_by], lazy="selectin")
    reviewer = relationship("User", foreign_keys=[reviewed_by], lazy="selectin")
