"""add positions to landing content

Revision ID: 015_add_positions
Revises: 014_create_academic_structure
Create Date: 2026-07-20

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '015_add_positions'
down_revision: Union[str, None] = '014_create_academic_structure'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('landing_page_content', sa.Column('positions', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('landing_page_content', 'positions')
