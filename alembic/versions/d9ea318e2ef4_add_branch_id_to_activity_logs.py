"""add_branch_id_to_activity_logs

Revision ID: d9ea318e2ef4
Revises: 59da0acbc792
Create Date: 2026-06-20 11:28:08.959759

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd9ea318e2ef4'
down_revision: Union[str, None] = '59da0acbc792'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'activity_logs',
        sa.Column('branch_id', sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        'fk_activity_logs_branch_id',
        'activity_logs', 'branches',
        ['branch_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_index('ix_activity_logs_branch_id', 'activity_logs', ['branch_id'])


def downgrade() -> None:
    op.drop_index('ix_activity_logs_branch_id', table_name='activity_logs')
    op.drop_constraint('fk_activity_logs_branch_id', 'activity_logs', type_='foreignkey')
    op.drop_column('activity_logs', 'branch_id')
