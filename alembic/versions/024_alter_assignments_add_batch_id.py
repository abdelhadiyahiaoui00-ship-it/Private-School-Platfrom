"""create_assignments_and_files_tables_with_batch_id

Revision ID: 024_add_batch_id
Revises: 023_attendance_idx
Create Date: 2026-08-27
"""
from typing import Union
from alembic import op
import sqlalchemy as sa

revision: str = '024_add_batch_id'
down_revision: Union[str, None] = '023_attendance_idx'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create assignments table (was never created in prior migrations)
    op.create_table(
        'assignments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('batch_id', sa.String(36), nullable=True),
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.Column('class_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('session_id', sa.Integer(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['class_id'], ['classes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
    )
    op.create_index('idx_assignments_batch_id', 'assignments', ['batch_id'])
    op.create_index('idx_assignments_group_id', 'assignments', ['group_id'])

    # Create assignment_files table
    op.create_table(
        'assignment_files',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('assignment_id', sa.Integer(), nullable=False),
        sa.Column('file_url', sa.String(500), nullable=False),
        sa.Column('file_type', sa.String(50), nullable=True),
        sa.Column('file_name', sa.String(255), nullable=True),
        sa.Column('uploaded_by', sa.Integer(), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['assignment_id'], ['assignments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index('idx_assignment_files_assignment_id', 'assignment_files', ['assignment_id'])


def downgrade() -> None:
    op.drop_index('idx_assignment_files_assignment_id', table_name='assignment_files')
    op.drop_table('assignment_files')
    op.drop_index('idx_assignments_group_id', table_name='assignments')
    op.drop_index('idx_assignments_batch_id', table_name='assignments')
    op.drop_table('assignments')
