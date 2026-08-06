from datetime import date
from typing import Optional
from sqlalchemy import (
    Date, ForeignKey, Integer, Numeric, SmallInteger, String
)
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
    # Education level targeting
    education_stage: Mapped[str] = mapped_column(
        String(20), nullable=False, default="all"
    )  # 'primary'|'middle'|'high'|'university'|'all'
    education_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    level_scope: Mapped[str] = mapped_column(
        String(20), nullable=False, default="all_levels"
    )  # 'specific'|'stage_and_above'|'age_range'|'all_levels'
    min_age: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    max_age: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    university_label: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    level_rank: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    # Computed on write per rank table in spec §2.3; NULL when level_scope='age_range'|'all_levels'
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    # 'active' | 'archived'
    created_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    branch = relationship("Branch", lazy="selectin")
    module = relationship("Module", lazy="selectin")
    teacher = relationship("User", lazy="selectin", foreign_keys=[teacher_id])
