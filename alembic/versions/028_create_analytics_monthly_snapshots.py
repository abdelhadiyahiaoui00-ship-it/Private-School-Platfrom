"""create_analytics_monthly_snapshots

Revision ID: 028_analytics_monthly_snapshots
Revises: 027_entity_tracking
Create Date: 2026-09-23
"""
from typing import Union
from alembic import op
import sqlalchemy as sa

revision: str = '028_analytics_monthly_snapshots'
down_revision: Union[str, None] = '027_entity_tracking'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'analytics_monthly_snapshots',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('branch_id', sa.Integer(), sa.ForeignKey('branches.id'), nullable=True),
        sa.Column('year', sa.SmallInteger(), nullable=False),
        sa.Column('month', sa.SmallInteger(), nullable=False),
        sa.Column('total_revenue', sa.Numeric(12, 2), nullable=False, server_default='0.00'),
        sa.Column('total_commissions', sa.Numeric(12, 2), nullable=False, server_default='0.00'),
        sa.Column('net_revenue', sa.Numeric(12, 2), nullable=False, server_default='0.00'),
        sa.Column('payment_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('new_enrollments', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('active_subscriptions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    try:
        op.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_analytics_monthly_snapshots_unique 
            ON analytics_monthly_snapshots (year, month, COALESCE(branch_id, 0));
        """)
    except Exception:
        pass


def downgrade() -> None:
    try:
        op.execute("DROP INDEX IF EXISTS idx_analytics_monthly_snapshots_unique;")
    except Exception:
        pass
    op.drop_table('analytics_monthly_snapshots')
