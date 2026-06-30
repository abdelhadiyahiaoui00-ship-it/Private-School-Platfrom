"""seed_system_config_default_row

Revision ID: 013_seed_config
Revises: 012_create_landing
Create Date: 2026-06-30

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '013_seed_config'
down_revision: Union[str, None] = '012_create_landing'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Only insert if row id=1 does not already exist (idempotent)
    op.execute("""
        INSERT INTO system_config (
            id, default_language, school_name,
            monthly_default_duration_days,
            monthly_expiry_warning_days,
            session_based_expiry_warning_sessions,
            about_stats, social_links
        )
        SELECT 1, 'ar', 'Académie Al-Nour', 30, 3, 3, '[]', '{}'
        WHERE NOT EXISTS (SELECT 1 FROM system_config WHERE id = 1)
    """)


def downgrade() -> None:
    op.execute("DELETE FROM system_config WHERE id = 1")
