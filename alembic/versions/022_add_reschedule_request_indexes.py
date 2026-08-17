"""add_reschedule_request_indexes

Revision ID: 022_reschedule_indexes
Revises: 021_attendance_status_check
"""
from typing import Sequence, Union

from alembic import op


revision: str = "022_reschedule_indexes"
down_revision: Union[str, None] = "021_attendance_status_check"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "idx_reschedule_requests_status",
        "session_reschedule_requests",
        ["status"],
    )
    op.create_index(
        "idx_reschedule_requests_session",
        "session_reschedule_requests",
        ["session_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("idx_reschedule_requests_session", table_name="session_reschedule_requests")
    op.drop_index("idx_reschedule_requests_status", table_name="session_reschedule_requests")
