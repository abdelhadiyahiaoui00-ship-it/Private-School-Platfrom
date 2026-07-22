from datetime import date
from typing import Optional
from sqlalchemy import Date, ForeignKey, Integer, JSON, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.common.base_model import BaseModel


class Group(BaseModel):
    __tablename__ = "groups"

    class_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    teacher_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    schedule: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # [{dayOfWeek: 0-6, startTime: "HH:MM", endTime: "HH:MM"}, ...]
    room: Mapped[str] = mapped_column(String(150), nullable=False)
    max_students: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    subscription_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # 'monthly' | 'session_based'
    session_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    # 'active' | 'archived'
    last_generated_until: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Relationships
    class_ = relationship("Class", lazy="selectin")
    teacher = relationship("User", lazy="selectin", foreign_keys=[teacher_id])
