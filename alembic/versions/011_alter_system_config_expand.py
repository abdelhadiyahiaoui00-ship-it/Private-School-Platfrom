"""alter_system_config_expand

Revision ID: 011_alter_system_config
Revises: 010_alter_branches
Create Date: 2026-06-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '011_alter_system_config'
down_revision: Union[str, None] = '010_alter_branches'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('system_config', sa.Column('logo_url', sa.Text(), nullable=True))
    op.add_column('system_config', sa.Column('wide_logo_url', sa.Text(), nullable=True))
    op.add_column('system_config', sa.Column('favicon_url', sa.Text(), nullable=True))
    op.add_column('system_config', sa.Column('about_title', sa.String(length=255), nullable=True))
    op.add_column('system_config', sa.Column('about_description', sa.Text(), nullable=True))
    op.add_column('system_config', sa.Column('about_stats', sa.JSON(), nullable=False, server_default='[]'))
    op.add_column('system_config', sa.Column('social_links', sa.JSON(), nullable=False, server_default='{}'))
    op.add_column('system_config', sa.Column('address', sa.Text(), nullable=True))
    op.add_column('system_config', sa.Column('founding_year', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('system_config', 'founding_year')
    op.drop_column('system_config', 'address')
    op.drop_column('system_config', 'social_links')
    op.drop_column('system_config', 'about_stats')
    op.drop_column('system_config', 'about_description')
    op.drop_column('system_config', 'about_title')
    op.drop_column('system_config', 'favicon_url')
    op.drop_column('system_config', 'wide_logo_url')
    op.drop_column('system_config', 'logo_url')
