"""create_landing_page_content

Revision ID: 012_create_landing
Revises: 011_alter_system_config
Create Date: 2026-06-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '012_create_landing'
down_revision: Union[str, None] = '011_alter_system_config'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'landing_page_content',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('section', sa.String(length=30), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('subtitle', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('image_url', sa.Text(), nullable=True),
        sa.Column('link_url', sa.Text(), nullable=True),
        sa.Column('badge', sa.String(length=20), nullable=True),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_landing_page_content_section', 'landing_page_content', ['section'])


def downgrade() -> None:
    op.drop_index('ix_landing_page_content_section', table_name='landing_page_content')
    op.drop_table('landing_page_content')
