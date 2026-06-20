from typing import Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column
from src.core.database import Base


class SystemConfig(Base):
    __tablename__ = "system_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    default_language: Mapped[str] = mapped_column(String(5), nullable=False, default="ar")
    school_name: Mapped[str] = mapped_column(String(200), nullable=False, default="Académie Al-Nour")
    contact_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    monthly_default_duration_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    monthly_expiry_warning_days: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    session_based_expiry_warning_sessions: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    updated_at: Mapped[Optional[object]] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    updated_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
