"""alter_system_config_add_assignment_due_soon_hours

Revision ID: 026_assignment_due_soon
Revises: 025_assignment_submissions
Create Date: 2026-08-27
"""
from typing import Union
from alembic import op
import sqlalchemy as sa

revision: str = '026_assignment_due_soon'
down_revision: Union[str, None] = '025_assignment_submissions'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('system_config', sa.Column(
        'assignment_due_soon_warning_hours',
        sa.Integer(),
        nullable=False,
        server_default='24'
    ))


def downgrade() -> None:
    op.drop_column('system_config', 'assignment_due_soon_warning_hours')
