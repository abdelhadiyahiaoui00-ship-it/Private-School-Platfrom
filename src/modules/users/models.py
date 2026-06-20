"""
Users + UserBranch + ParentStudentLink models — Sprint 1.
"""
from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Numeric,
    ForeignKey,
    Integer,
    JSON,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import relationship as orm_relationship

from src.core.database import Base
from src.common.base_model import BaseModel
from src.modules.branches.models import Branch  # Ensure Branch is in the registry


class User(BaseModel):
    __tablename__ = "users"

    # ─── Identity ─────────────────────────────────────────────────────────────
    email: Mapped[Optional[str]] = mapped_column(
        String(255), unique=True, nullable=True, index=True
    )
    phone: Mapped[Optional[str]] = mapped_column(
        String(30), unique=True, nullable=True, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # ─── Role & Status ────────────────────────────────────────────────────────
    role: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    # 'owner' | 'superAdmin' | 'admin' | 'teacher' | 'student' | 'parent'
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active", index=True
    )
    # 'active' | 'inactive'

    # ─── Profile ──────────────────────────────────────────────────────────────
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    # 'male' | 'female'

    # ─── Admin permissions (JSONB, only meaningful for role='admin') ──────────
    permissions: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # {manageUsers, manageClasses, manageSessions,
    #  manageEnrollments, manageSubscriptions, viewLogs}: bool

    # ─── Teacher-specific ─────────────────────────────────────────────────────
    default_commission_percent: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 2), nullable=True
    )

    # ─── System fields ────────────────────────────────────────────────────────
    language: Mapped[str] = mapped_column(String(5), nullable=False, default="ar")
    # 'ar' | 'fr' | 'en'
    must_change_password: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    notifications_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deactivated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deactivated_by: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ─── Relationships ────────────────────────────────────────────────────────
    branch_links: Mapped[list["UserBranch"]] = orm_relationship(
        "UserBranch",
        back_populates="user",
        foreign_keys="UserBranch.user_id",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    # parent→student links (this user is the PARENT)
    linked_students: Mapped[list["ParentStudentLink"]] = orm_relationship(
        "ParentStudentLink",
        back_populates="parent",
        foreign_keys="ParentStudentLink.parent_id",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    # student→parent links (this user is the STUDENT)
    linked_parents: Mapped[list["ParentStudentLink"]] = orm_relationship(
        "ParentStudentLink",
        back_populates="student",
        foreign_keys="ParentStudentLink.student_id",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    @property
    def assigned_branches(self) -> list["Branch"]:
        return [ub.branch for ub in self.branch_links if ub.branch]

    @property
    def children_count(self) -> int:
        return len(self.linked_students)


class UserBranch(Base):
    """Join table: user ↔ branch assignment."""
    __tablename__ = "user_branches"

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
        index=True,
    )
    branch_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("branches.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
        index=True,
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # ─── Relationships ────────────────────────────────────────────────────────
    user: Mapped["User"] = orm_relationship(
        "User", back_populates="branch_links", foreign_keys="UserBranch.user_id"
    )
    branch: Mapped["Branch"] = orm_relationship("Branch", lazy="selectin")  # type: ignore[name-defined]


class ParentStudentLink(Base):
    """Many-to-many: parent user ↔ student user."""
    __tablename__ = "parent_student_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    parent_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relationship: Mapped[str] = mapped_column(
        String(30), nullable=False, default="parent"
    )
    # 'parent' | 'guardian' | 'sibling' | 'other'
    created_by: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # ─── Relationships ────────────────────────────────────────────────────────
    parent: Mapped["User"] = orm_relationship(
        "User", back_populates="linked_students", foreign_keys="ParentStudentLink.parent_id"
    )
    student: Mapped["User"] = orm_relationship(
        "User", back_populates="linked_parents", foreign_keys="ParentStudentLink.student_id"
    )
