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


def upgrade() -> None:
    op.create_check_constraint(
        "chk_attendance_status",
        "attendance",
        "status IN ('present', 'absent', 'excused')",
    )
    op.add_column(
        "attendance",
        sa.Column(
            "session_consumed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "attendance",
        sa.Column(
            "is_override",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("attendance", "is_override")
    op.drop_column("attendance", "session_consumed")
    op.drop_constraint("chk_attendance_status", "attendance", type_="check")
