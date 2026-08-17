"""alter_attendance_add_status_check

Revision ID: 021_attendance_status_check
Revises: b38d3cf87aa9
Create Date: 2026-07-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "021_attendance_status_check"
down_revision: Union[str, None] = "b38d3cf87aa9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    return sa.inspect(bind).has_table(table_name)


def _column_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    return {column["name"] for column in sa.inspect(bind).get_columns(table_name)}


def _check_constraint_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    return {
        constraint["name"]
        for constraint in sa.inspect(bind).get_check_constraints(table_name)
    }


def upgrade() -> None:
    if not _table_exists("attendance"):
        op.create_table(
            "attendance",
            sa.Column("session_id", sa.Integer(), nullable=False),
            sa.Column("student_id", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(length=10), nullable=False),
            sa.Column(
                "session_consumed",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
            sa.Column(
                "is_override",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
            sa.Column(
                "marked_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=True,
            ),
            sa.Column("marked_by", sa.Integer(), nullable=True),
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.CheckConstraint(
                "status IN ('present', 'absent', 'excused')",
                name="chk_attendance_status",
            ),
            sa.ForeignKeyConstraint(
                ["session_id"], ["sessions.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(["student_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["marked_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_attendance_session_id", "attendance", ["session_id"])
        op.create_index("ix_attendance_student_id", "attendance", ["student_id"])
        return

    columns = _column_names("attendance")
    if "session_consumed" not in columns:
        op.add_column(
            "attendance",
            sa.Column(
                "session_consumed",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
        )
    if "is_override" not in columns:
        op.add_column(
            "attendance",
            sa.Column(
                "is_override",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
        )
    if "created_at" not in columns:
        op.add_column(
            "attendance",
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
        )
    if "updated_at" not in columns:
        op.add_column(
            "attendance",
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
        )
    if "chk_attendance_status" not in _check_constraint_names("attendance"):
        op.create_check_constraint(
            "chk_attendance_status",
            "attendance",
            "status IN ('present', 'absent', 'excused')",
        )


def downgrade() -> None:
    if not _table_exists("attendance"):
        return

    columns = _column_names("attendance")
    constraints = _check_constraint_names("attendance")
    if "is_override" in columns:
        op.drop_column("attendance", "is_override")
    if "session_consumed" in columns:
        op.drop_column("attendance", "session_consumed")
    if "chk_attendance_status" in constraints:
        op.drop_constraint("chk_attendance_status", "attendance", type_="check")
