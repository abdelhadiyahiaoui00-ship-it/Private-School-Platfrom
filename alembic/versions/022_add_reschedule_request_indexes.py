"""add_reschedule_request_indexes

Revision ID: 022_reschedule_indexes
Revises: 021_attendance_status_check
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "022_reschedule_indexes"
down_revision: Union[str, None] = "021_attendance_status_check"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    return sa.inspect(bind).has_table(table_name)


def _column_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    return {column["name"] for column in sa.inspect(bind).get_columns(table_name)}


def _index_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    return {index["name"] for index in sa.inspect(bind).get_indexes(table_name)}


def upgrade() -> None:
    if not _table_exists("session_reschedule_requests"):
        op.create_table(
            "session_reschedule_requests",
            sa.Column("session_id", sa.Integer(), nullable=False),
            sa.Column("requested_by", sa.Integer(), nullable=False),
            sa.Column("reason", sa.Text(), nullable=False),
            sa.Column("proposed_date", sa.Date(), nullable=False),
            sa.Column("proposed_start_time", sa.Time(), nullable=False),
            sa.Column("proposed_end_time", sa.Time(), nullable=False),
            sa.Column("proposed_room", sa.String(length=150), nullable=True),
            sa.Column(
                "status",
                sa.String(length=20),
                nullable=False,
                server_default="pending",
            ),
            sa.Column("reviewed_by", sa.Integer(), nullable=True),
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("rejection_reason", sa.Text(), nullable=True),
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
            sa.ForeignKeyConstraint(["session_id"], ["sessions.id"]),
            sa.ForeignKeyConstraint(["requested_by"], ["users.id"]),
            sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_session_reschedule_requests_session_id",
            "session_reschedule_requests",
            ["session_id"],
        )
    else:
        columns = _column_names("session_reschedule_requests")
        if "updated_at" not in columns:
            op.add_column(
                "session_reschedule_requests",
                sa.Column(
                    "updated_at",
                    sa.DateTime(timezone=True),
                    server_default=sa.text("now()"),
                    nullable=False,
                ),
            )

    indexes = _index_names("session_reschedule_requests")
    if "idx_reschedule_requests_status" not in indexes:
        op.create_index(
            "idx_reschedule_requests_status",
            "session_reschedule_requests",
            ["status"],
        )
    if "idx_reschedule_requests_session" not in indexes:
        op.create_index(
            "idx_reschedule_requests_session",
            "session_reschedule_requests",
            ["session_id", "status"],
        )


def downgrade() -> None:
    if not _table_exists("session_reschedule_requests"):
        return

    indexes = _index_names("session_reschedule_requests")
    if "idx_reschedule_requests_session" in indexes:
        op.drop_index(
            "idx_reschedule_requests_session",
            table_name="session_reschedule_requests",
        )
    if "idx_reschedule_requests_status" in indexes:
        op.drop_index(
            "idx_reschedule_requests_status",
            table_name="session_reschedule_requests",
        )
