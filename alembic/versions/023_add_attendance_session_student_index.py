"""add_attendance_session_student_index

Revision ID: 023_attendance_idx
Revises: 022_reschedule_indexes
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "023_attendance_idx"
down_revision: Union[str, None] = "022_reschedule_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    return sa.inspect(bind).has_table(table_name)


def _index_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    return {index["name"] for index in sa.inspect(bind).get_indexes(table_name)}


def upgrade() -> None:
    if not _table_exists("attendance"):
        return

    if "idx_attendance_session_student" not in _index_names("attendance"):
        op.create_index(
            "idx_attendance_session_student",
            "attendance",
            ["session_id", "student_id"],
        )


def downgrade() -> None:
    if not _table_exists("attendance"):
        return

    if "idx_attendance_session_student" in _index_names("attendance"):
        op.drop_index("idx_attendance_session_student", table_name="attendance")
