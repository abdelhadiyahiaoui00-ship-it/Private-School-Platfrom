"""alter_system_config_add_about_video_art_image

Revision ID: 030_system_config_about_video_art_image
Revises: 029_analytics_teacher_monthly_snapshots
Create Date: 2026-09-25
"""
from typing import Union
from alembic import op
import sqlalchemy as sa

revision: str = '030_config_about_video_art_img'
down_revision: Union[str, None] = '029_teacher_monthly_snapshots'

branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE system_config ADD COLUMN IF NOT EXISTS about_video_url TEXT")
    op.execute("ALTER TABLE system_config ADD COLUMN IF NOT EXISTS art_under_image_url TEXT")



def downgrade() -> None:
    op.drop_column('system_config', 'art_under_image_url')
    op.drop_column('system_config', 'about_video_url')
