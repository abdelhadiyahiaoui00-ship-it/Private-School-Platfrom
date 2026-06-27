"""alter_branches_full_schema

Revision ID: 010_alter_branches
Revises: d9ea318e2ef4
Create Date: 2026-06-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '010_alter_branches'
down_revision: Union[str, None] = 'd9ea318e2ef4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('branches', sa.Column('address', sa.Text(), nullable=True))
    op.add_column('branches', sa.Column('phone', sa.String(length=30), nullable=True))
    op.add_column('branches', sa.Column('email', sa.String(length=255), nullable=True))
    op.add_column('branches', sa.Column('latitude', sa.Numeric(precision=10, scale=7), nullable=True))
    op.add_column('branches', sa.Column('longitude', sa.Numeric(precision=10, scale=7), nullable=True))
    op.add_column('branches', sa.Column('map_embed_url', sa.Text(), nullable=True))
    op.add_column('branches', sa.Column('photo_urls', postgresql.ARRAY(sa.Text()), nullable=False, server_default='{}'))
    op.add_column('branches', sa.Column('description', sa.Text(), nullable=True))
    op.create_unique_constraint('uq_branches_name', 'branches', ['name'])


def downgrade() -> None:
    op.drop_constraint('uq_branches_name', 'branches', type_='unique')
    op.drop_column('branches', 'description')
    op.drop_column('branches', 'photo_urls')
    op.drop_column('branches', 'map_embed_url')
    op.drop_column('branches', 'longitude')
    op.drop_column('branches', 'latitude')
    op.drop_column('branches', 'email')
    op.drop_column('branches', 'phone')
    op.drop_column('branches', 'address')
