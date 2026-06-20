"""
Branches model — Sprint 1 scaffold.
Full schema (address, phone, email, photos, coordinates) added in Sprint 2 migration.
"""
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.common.base_model import BaseModel


class Branch(BaseModel):
    __tablename__ = "branches"

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # ─── Relationships ────────────────────────────────────────────────────────
    # user_branches populated via UserBranch join table (defined in users module)
