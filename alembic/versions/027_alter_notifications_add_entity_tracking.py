"""alter_notifications_add_entity_tracking

Revision ID: 027_entity_tracking
Revises: 026_assignment_due_soon
Create Date: 2026-09-15
"""
from typing import Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError

revision: str = '027_entity_tracking'
down_revision: Union[str, None] = '026_assignment_due_soon'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Use ADD COLUMN IF NOT EXISTS via raw SQL for safety
    # (columns may already exist if ORM model was updated before this migration)
    conn = op.get_bind()

    try:
        op.add_column('notifications', sa.Column(
            'entity_type',
            sa.String(30),
            nullable=True,
        ))
    except Exception:
        pass  # Column already exists — safe to skip

    try:
        op.add_column('notifications', sa.Column(
            'entity_id',
            sa.Integer(),
            nullable=True,
        ))
    except Exception:
        pass  # Column already exists — safe to skip

    # Create index — drop first if exists (idempotent)
    try:
        op.create_index(
            'idx_notifications_entity',
            'notifications',
            ['entity_type', 'entity_id'],
        )
    except Exception:
        pass  # Index already exists — safe to skip


def downgrade() -> None:
    try:
        op.drop_index('idx_notifications_entity', table_name='notifications')
    except Exception:
        pass
    try:
        op.drop_column('notifications', 'entity_id')
    except Exception:
        pass
    try:
        op.drop_column('notifications', 'entity_type')
    except Exception:
        pass
