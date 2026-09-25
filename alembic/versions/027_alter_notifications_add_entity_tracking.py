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
    op.execute("ALTER TABLE notifications ADD COLUMN IF NOT EXISTS entity_type VARCHAR(30)")
    op.execute("ALTER TABLE notifications ADD COLUMN IF NOT EXISTS entity_id INTEGER")
    op.execute("CREATE INDEX IF NOT EXISTS idx_notifications_entity ON notifications (entity_type, entity_id)")



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
