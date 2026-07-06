from datetime import date
from typing import Optional
from sqlalchemy import Date, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.common.base_model import BaseModel


class Class(BaseModel):
    __tablename__ = "classes"

    branch_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("branches.id"), nullable=False, index=True
    )
    module_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("modules.id"), nullable=False, index=True
    )
    teacher_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    period_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    period_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    commission_percent: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active"
    )
    # 'active' | 'archived'

    # ─── Relationships (read-only for Sprint 3) ───────────────────────────────
    branch = relationship("Branch", lazy="selectin")
    module = relationship("Module", lazy="selectin")
    teacher = relationship("User", lazy="selectin", foreign_keys=[teacher_id])
